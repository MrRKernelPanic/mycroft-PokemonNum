# Copyright 2017 Mycroft AI Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import time
import pickle
import re

from adapt.intent import IntentBuilder
from mycroft.skills.core import (
    MycroftSkill,
    intent_handler,
    intent_file_handler)
from mycroft.util.log import LOG
from mycroft.audio import wait_while_speaking, is_speaking
from datetime import datetime, timedelta
from os.path import join, isfile, abspath, dirname
from mycroft.util import play_wav
from mycroft.messagebus.message import Message
from mycroft.util.parse import extract_number, fuzzy_match, extract_duration
from mycroft.util.format import pronounce_number, nice_duration, join_list
from mycroft.util.time import now_local
from num2words import num2words

try:
    from mycroft.skills.skill_data import to_alnum
except ImportError:
    from mycroft.skills.skill_data import to_letters as to_alnum

# TESTS
#  0: cancel all timers
#  1: start a timer > 1 minute
#  2: cancel timer
#  3: start a 30 second timer
#  4: cancel timer
#  5: start a 1 hour timer
#  6: start a 20 minute timer
#  7: how much time is left
#  8: start a 1 hour timer
#  9: start a 20 minute timer
# 10: how much time is left > first
# 11: how much time is left on 5 minute timer
# 12: how much is left on the five minute timer
# 13: start a 7 minute timer called lasagna
# 14: how much is left on the lasagna timer
# 15: set a 1 and a half minute timer
# 16: set a timer for 3 hours 45 minutes

#####################################################################


class TimerSkill(MycroftSkill):
    def __init__(self):
        super(TimerSkill, self).__init__("TimerSkill")
        self.active_timers = []
        self.beep_repeat_period = 10
        self.sound_file = join(abspath(dirname(__file__)), 'twoBeep.wav')
        self.beep_repeat_period = 5

        self.displaying_timer = None
        self.beep_process = None
        self.mute = False
        self.timer_index = 0
        self.display_idx = None

        # Threshold score for Fuzzy Logic matching for Timer Name
        self.threshold = 0.7

    def initialize(self):
        self.register_entity_file('duration.entity')
        #self.register_entity_file('timervalue.entity')

        self.unpickle()

        # Invoke update_display in one second to allow it to disable the
        # cancel intent, since there are no timers to cancel yet!
        self.schedule_repeating_event(self.update_display,
                                      None, 1, name='ShowTimer')

        # To prevent beeping while listening
        self.is_listening = False
        self.add_event('recognizer_loop:record_begin',
                       self.handle_listener_started)
        self.add_event('recognizer_loop:record_end',
                       self.handle_listener_ended)
        self.add_event('skill.mycrofttimer.verify.cancel',
                       self.handle_verify_stop_timer)

    def pickle(self):
        # Save the timers for reload
        self.do_pickle('save_timers', self.active_timers)

    def unpickle(self):
        # Reload any saved timers
        self.active_timers = self.do_unpickle('save_timers', [])

        # Reset index
        self.timer_index = 0
        for timer in self.active_timers:
            if timer["index"] > self.timer_index:
                self.timer_index = timer["index"]

    # TODO: Implement util.is_listening() to replace this
    def handle_listener_started(self, message):
        self.is_listening = True

    def handle_listener_ended(self, message):
        self.is_listening = False

    def _extract_duration(self, text):
        """ Extract duration in seconds
        Args:
            text (str): Full request, e.g. "set a 30 second timer"
        Returns:
            (int): Seconds requested, or None
            (str): Remainder of utterance
        """
        if not text:
            return None, None

        # Some STT engines return "30-second timer" not "30 second timer"
        # Deal with that before calling extract_duration().
        # TODO: Fix inside parsers
        utt = text.replace("-", " ")

        (dur_remainder, str_remainder) = extract_duration(utt, self.lang)
        if dur_remainder:
            return dur_remainder.total_seconds(), str_remainder
        return None, text

    def _extract_ordinal(self, text):
        num = None
        if text is None or len(text) == 0:
            return None

        try:
            num = extract_number(text, self.lang, ordinals=True)
            # TODO does this need to be converted to an int?
        except:
            self.log.debug('_extract_ordinal: ' +
                          'Error in extract_number process')
            pass
        if not num:
            try:
                # Should be removed if the extract_number() function can
                # parse ordinals already e.g. 1st, 3rd, 69th, etc.
                results = regex.search(r'(?b)\b((?P<Numeral>\d+)(st|nd|rd|th))\b', text)
                if (results) and (results['Numeral']):
                    num = int(results['Numeral'])
            except:
                self.log.debug('_extract_ordinal: ' +
                              'Error in _read_ordinal_from_text process')
                pass
        return num

    def _get_timer_name(self, utt):
        rx_file = self.find_resource('name.rx', 'regex')
        if utt and rx_file:
            with open(rx_file) as f:
                for pat in f.read().splitlines():
                    pat = pat.strip()
                    if pat and pat[0] == "#":
                        continue
                    res = re.search(pat, utt)
                    if res:
                        try:
                            # self.log.info('regex name extraction: ' + str(res.group("Name")))
                            name = res.group("Name")
                            if name and len(name.strip()) > 0:
                                return name
                        except IndexError:
                            pass
        return None

    def _get_next_timer(self):
        # Retrieve the next timer set to trigger
        next = None
        for timer in self.active_timers:
            if not next or timer["expires"] < next["expires"]:
                next = timer
        return next

    def _get_ordinal_of_new_timer(self, duration, timers=None):
        # add a "Second" or "Third" of timers of same duration exist
        timers = timers or self.active_timers
        timer_count = sum(1 for t in timers if t["duration"] == duration)
        return timer_count + 1

    def _get_speakable_ordinal(self, timer):
        # Check if the timer with the following duration is the only one
        # of its kind or has other timers with the same duration
        timers = self.active_timers
        ordinal = timer['ordinal']
        duration = timer['duration']
        timer_count = sum(1 for t in timers if t["duration"] == duration)
        if timer_count > 1 or ordinal > 1:
            return num2words(ordinal, to="ordinal", lang=self.lang)
        else:
            return ""

    def _get_speakable_timer_list(self, timer_list):
        speakable_timer_list = []
        for timer in timer_list:
            dialog = 'timer.details'
            if timer['name'] is not None:
                dialog += '.named'
            data = {'ordinal': self._get_speakable_ordinal(timer),
                    'duration': nice_duration(timer["duration"]),
                    'name': timer['name']}
            speakable_timer_list.append(self.translate(dialog, data))
        names = join_list(speakable_timer_list, self.translate("and"))
        return names

    def _get_timer_matches(self, utt, timers=None, max_results=1,
                           dialog='ask.which.timer', is_response=False):
        self.log.info("-----------GET-TIMER-----------")
        timers = timers or self.active_timers
        all_words = self.translate_list('all')
        # self.log.info("Utt initial: " + utt)
        if timers is None or len(timers) == 0:
            self.log.error("Cannot get match. No active timers.")
            return None
        elif utt and any(i.strip() in utt for i in all_words):
            return timers
        # self.log.info("timers: " + str(timers))
        duration, utt = self._extract_duration(utt)
        # self.log.info("duration: " + str(duration))
        # self.log.info("Utt returned: " + utt)
        ordinal = self._extract_ordinal(utt)
        timers_have_ordinals = any(t['ordinal'] > 1 for t in timers)
        # self.log.info("timers_have_ordinals: " + str(timers_have_ordinals))
        # self.log.info("ordinal: " + str(ordinal))
        # self.log.info("ordinal: " + str(type(ordinal)))
        name = self._get_timer_name(utt)
        if is_response and name == None:
            # Catch direct naming of a timer when asked eg "pasta"
            name = utt
        # self.log.info("name: " + str(name))

        duration_matches, name_matches = None, None
        if duration:
            duration_matches = [t for t in timers if duration == t['duration']]
            # self.log.info("duration_matches:")
            # self.log.info(duration_matches)
        if name:
            self.log.info("name: " + name)
            name_matches = [t for t in timers
                            if t['name']
                            and fuzzy_match(name,t['name']) > self.threshold]
            self.log.info("name_matches:")
            self.log.info(name_matches)

        # TODO Test these branches
        if duration_matches and name_matches:
            matches = [t for t in name_matches if duration == t['duration']]
            self.log.info("and_matches:")
            self.log.info(matches)
        elif duration_matches or name_matches:
            matches = duration_matches or name_matches
            self.log.info("or_matches:")
            self.log.info(matches)
        else:
            matches = timers
            self.log.info("neither_matches:")

        if ordinal and len(matches) > 1:
            for match in matches:
                ord_to_match = (match['ordinal'] if timers_have_ordinals
                                                 else match['index'])
                if ordinal == ord_to_match:
                    return [match]
        elif len(matches) <= max_results:
            return matches
        elif len(matches) > max_results:
            # TODO addition = the group currently spoken eg "5 minute timers" or "pasta timers"
            additional = ""
            speakable_matches = self._get_speakable_timer_list(matches)
            reply = self.get_response(dialog,
                                      data={"count": len(matches),
                                            "names": speakable_matches,
                                            "additional": additional})
            wait_while_speaking()
            if reply:
                return self._get_timer_matches(reply,
                                                   timers=matches,
                                                   dialog=dialog,
                                                   max_results=max_results,
                                                   is_response=True)
            else:
                return "User Cancelled"
        else:
            return None

    def update_display(self, message):
        # Get the next triggering timer
        timer = self._get_next_timer()
        if not timer:
            # No active timers, clean up
            self.cancel_scheduled_event('ShowTimer')
            self.displaying_timer = None
            self.disable_intent("handle_mute_timer")
            self._stop_beep()
            self.enclosure.eyes_reset()
            self.enclosure.mouth_reset()
            return

        # Check if there is an expired timer
        now = datetime.now()
        flash = False
        for timer in self.active_timers:
            if timer["expires"] < now:
                flash = True
                break
        if flash:
            if now.second % 2 == 1:
                self.enclosure.eyes_on()
            else:
                self.enclosure.eyes_off()

        if is_speaking():
            # Don't overwrite mouth visemes
            return

        if len(self.active_timers) > 1:
            # This code will display each timer for 5 passes of this
            # screen update (5 seconds), then move on to display next timer.
            if not self.display_idx:
                self.display_idx = 1.0
            else:
                self.display_idx += 0.2
            if int(self.display_idx-1) >= len(self.active_timers):
                self.display_idx = 1.0

            timer = self.active_timers[int(self.display_idx)-1]
            idx = timer["index"]
        else:
            if self.display_idx:
                self.enclosure.mouth_reset()
            self.display_idx = None
            idx = None

        # Check if the display frequency is set correctly for closest timer.
        if timer != self.displaying_timer:
            self.cancel_scheduled_event('ShowTimer')
            self.schedule_repeating_event(self.update_display,
                                          None, 1,
                                          name='ShowTimer')
            self.displaying_timer = timer

        # Calc remaining time and show using faceplate
        if (timer["expires"] > now):
            # Timer still running
            remaining = (timer["expires"] - now).seconds
            self.render_timer(idx, remaining)
        else:
            # Timer has expired but not been cleared, flash eyes
            overtime = (now - timer["expires"]).seconds
            self.render_timer(idx, -overtime)

            if timer["announced"]:
                # beep again every 10 seconds
                if overtime % self.beep_repeat_period == 0 and not self.mute:
                    self._play_beep()
            else:
                # if only timer, just beep
                if len(self.active_timers) == 1:
                    self._play_beep()
                else:
                    name = timer['name'] or nice_duration(timer["duration"])
                    self.speak_dialog("timer.expired",
                                      data={"name": name,
                                            "ordinal": self._get_speakable_ordinal(timer)})
                timer["announced"] = True

    def render_timer(self, idx, seconds):
        display_owner = self.enclosure.display_manager.get_active()
        if display_owner == "":
            self.enclosure.mouth_reset()  # clear any leftover bits
        elif display_owner != "TimerSkill":
            return

        # convert seconds to m:ss or h:mm:ss
        if seconds <= 0:
            expired = True
            seconds *= -1
        else:
            expired = False

        hours = seconds // (60*60)  # hours
        rem = seconds % (60*60)
        minutes = rem // 60  # minutes
        seconds = rem % 60
        if hours > 0:
            # convert to h:mm:ss
            time = (str(hours) + ":"+str(minutes).zfill(2) +
                    ":"+str(seconds).zfill(2))
            # account of colons being smaller
            pixel_width = len(time)*4 - 2*2 + 6
        else:
            # convert to m:ss
            time = str(minutes).zfill(2)+":"+str(seconds).zfill(2)
            # account of colons being smaller
            pixel_width = len(time)*4 - 2 + 6

        x = (4*8 - pixel_width) // 2  # centers on display
        if expired:
            time = "-"+time
        else:
            time = " "+time

        if idx:
            # If there is an index to show, display at the left
            png = join(abspath(dirname(__file__)), str(int(idx))+".png")
            self.enclosure.mouth_display_png(png, x=3, y=2, refresh=False)
            x += 6

        # draw on the display
        for ch in time:
            # deal with some odd characters that can break filesystems
            if ch == ":":
                png = "colon.png"
            elif ch == " ":
                png = "blank.png"
            elif ch == "-":
                png = "negative.png"
            else:
                png = ch+".png"

            png = join(abspath(dirname(__file__)), png)
            self.enclosure.mouth_display_png(png, x=x, y=2, refresh=False)
            if ch == ':':
                x += 2
            else:
                x += 4

    def _speak_timer(self, timer):
        # If _speak_timer receives timer = None, it assumes that timer
        # wasn't found, and not there was no active timers
        if timer is None:
            self.speak_dialog("timer.not.found")
            return

        # TODO: speak_dialog should have option to not show mouth
        # For now, just deactiveate.  The sleep() is to allow the
        # message to make it across the bus first.
        self.enclosure.deactivate_mouth_events()
        time.sleep(0.25)

        now = datetime.now()
        name = timer["name"] or nice_duration(timer["duration"])
        ordinal = timer["ordinal"]

        if timer and timer["expires"] < now:
            # expired, speak how long since it triggered
            time_diff = nice_duration((now - timer["expires"]).seconds)
            dialog = 'time.elapsed'
        else:
            # speak remaining time
            time_diff = nice_duration((timer["expires"] - now).seconds)
            dialog = 'time.remaining'

        speakable_ord = self._get_speakable_ordinal(timer)
        if speakable_ord != "":
            dialog += '.ordinal'

        self.speak_dialog(dialog, {"name": name,
                                   "time_diff": time_diff,
                                   "ordinal": speakable_ord})
        wait_while_speaking()
        self.enclosure.activate_mouth_events()

    def _speak_timer_status(self, timer_name, has_all):
        self.log.info("_speak_timer_status")
        # Check if utterance has "All"
        if (timer_name is None or has_all):
            for timer in self.active_timers:
                self._speak_timer(timer)
            return
        # Just speak status of given timer
        timer = self._get_timer_matches(timer_name, "ask.which.timer")
        return self._speak_timer(timer)

    ######################################################################
    # INTENT HANDLERS

    def handle_start_timer(self, message):
        utt = message.data["utterance"]
        #~~ GET TIMER DURATION
        secs, utt_remaining = self._extract_duration(utt)
        if secs and secs == 1:  # prevent "set one timer" doing 1 sec timer
            utt_remaining = message.data["utterance"]

        if secs == None: # no duration found, request from user
            req_duration = self.get_response('ask.how.long')
            secs, _ = self._extract_duration(req_duration)
            if secs is None:
                return  # user cancelled

        #~~ GET TIMER NAME
        if utt_remaining is not None and len(utt_remaining) > 0:
            timer_name = self._get_timer_name(utt_remaining)
        else:
            timer_name = None

        #~~ SHOULD IT BE AN ALARM?
        # TODO: add name of alarm if available?
        if secs >= 60*60*24:  # 24 hours in seconds
            if self.ask_yesno("timer.too.long.alarm.instead") == 'yes':
                alarm_time = now_local() + timedelta(seconds=secs)
                phrase = self.translate('set.alarm',
                                        {'date': alarm_time.strftime('%B %d %Y'),
                                         'time': alarm_time.strftime('%I:%M%p')})
                self.bus.emit(Message("recognizer_loop:utterance",
                                      {"utterances": [phrase], "lang": "en-us"}))
            return

        #~~ CREATE TIMER
        self.timer_index += 1
        time_expires = datetime.now() + timedelta(seconds=secs)
        timer = {"name": timer_name,
                 "index": self.timer_index,
                 # keep track of ordinal until all timers of that name expire
                 "ordinal": self._get_ordinal_of_new_timer(secs),
                 "duration": secs,
                 "expires": time_expires,
                 "announced": False}
        self.active_timers.append(timer)
        self.log.info("-------------TIMER-CREATED-------------")
        for key in timer:
            self.log.info(f'creating timer: {key}: {timer[key]}')
        self.log.info("---------------------------------------")

        #~~ INFORM USER
        if timer['ordinal'] > 1:
            dialog = 'started.ordinal.timer'
        elif len(self.active_timers) > 1:
            dialog = 'started.another.timer'
        else:
            dialog = 'started.timer'
        if timer['name'] is not None:
            dialog += '.with.name'

        self.speak_dialog(dialog,
                          data={"duration": nice_duration(timer["duration"]),
                                "name": timer["name"],
                                "ordinal": self._get_speakable_ordinal(timer)})

        #~~ CLEANUP
        self.pickle()
        wait_while_speaking()
        self.enable_intent("handle_mute_timer")
        # Start showing the remaining time on the faceplate
        self.update_display(None)
        # reset the mute flag with a new timer
        self.mute = False

    @intent_handler(IntentBuilder("start.timer.intent").require("Start").
                optionally("Connector").require("Timer"))
    def handle_start_timer_required(self, message):
        self.handle_start_timer(message)

    @intent_handler(IntentBuilder("start.timer.simple.intent").
                optionally("Start").optionally("Connector").require("Timer"))
    def handle_start_timer_simple(self, message):
        self.handle_start_timer(message)

    # Handles 'How much time left'
    @intent_file_handler('timer.status.intent')
    def handle_status_timer_padatious(self, message):
        self.handle_status_timer(message)

    @intent_handler(IntentBuilder("status.timer.intent").optionally("Query").
                require("Status").one_of("Timer", "Time").optionally("All").
                optionally("Duration").optionally("Name"))
    def handle_status_timer(self, message):
        self.log.info("--------------------------------------")
        for key in message.data:
            self.log.info(f'handle_status_timer: {key}: {message.data[key]}')
        self.log.info("--------------------------------------")

        if not self.active_timers:
            self.speak_dialog("no.active.timer")
            return

        utt = message.data["utterance"]

        self.log.info("-----------------------")
        self.log.info("handle_status_timer: List of Active Timers")
        for timer in self.active_timers:
           self.log.info(f'{timer["index"]}: Timer: {timer["name"]} Ordinal: {timer["ordinal"]} Duration: {timer["duration"]}')
        self.log.info("-----------------------")

        # If asking about all, or only 1 timer exists then speak
        if len(self.active_timers) == 1:
            timer_matches = self.active_timers
        else:
            # get max 2 matches, unless user explicitly asks for all
            timer_matches = self._get_timer_matches(utt, max_results=2)
        if timer_matches == "User Cancelled":
            return
        if timer_matches is None:
            self.speak_dialog('timer.not.found')
        else:
            for timer in timer_matches:
                self._speak_timer(timer)

    @intent_handler(IntentBuilder("").require("Mute").require("Timer"))
    def handle_mute_timer(self, message):
        self.mute = True

    @intent_file_handler('stop.timer.intent')
    def handle_stop_timer(self, message):
        self.log.info("--------------------------------------")
        for key in message.data:
            self.log.info(f'handle_stop_timer: {key}: {message.data[key]}')
        self.log.info("--------------------------------------")
        timer = self._get_next_timer()
        if timer and timer["expires"] < datetime.now():
            # Timer is beeping requiring no confirmation reaction,
            # treat it like a stop button press
            self.stop()
        else:
            self.handle_cancel_timer(message)

    @intent_handler(IntentBuilder("").require("Cancel").require("Timer").
                    optionally("All").optionally("Duration").
                    optionally("Name"))
    def handle_cancel_timer(self, message=None):
        utt = message.data['utterance']
        self.log.info("--------------------------------------")
        if message:
            for key in message.data:
                self.log.info(f'handle_cancel_timer: {key}: {message.data[key]}')
        self.log.info("--------------------------------------")
        self.log.info(f'handle_cancel_timer: {utt}')

        all_words = self.translate_list('all')
        self.log.info("message.data['All']: " + str(message.data.get('All')))
        has_all = any(i.strip() in utt for i in all_words) or message.data.get('All')
        num_timers = len(self.active_timers)

        if num_timers == 0:
            self.speak_dialog("no.active.timer")

        elif not message or has_all:
            if num_timers == 1:
                # Either "cancel all" or from Stop button
                timer = self._get_next_timer()
                self.speak_dialog("cancelled.single.timer")
            else:
                self.speak_dialog('cancel.all', data={"count": num_timers})

            # get duplicate so we can walk the list
            active_timers = list(self.active_timers)
            for timer in active_timers:
                self.cancel_timer(timer)
            self.pickle()   # save to disk

        elif num_timers == 1:
            # TODO: Cancel if there is a spoken name and it is a mismatch?
            # E.g. "Cancel the 5 minute timer" when it's a 7 minute timer
            timer = self._get_next_timer()
            self.cancel_timer(timer)
            duration = nice_duration(timer["duration"])
            self.speak_dialog("cancelled.single.timer")
            self.pickle()   # save to disk

        elif num_timers > 1:
            dialog = 'ask.which.timer.cancel'
            timer = self._get_timer_matches(utt, dialog=dialog, max_results=1)
            if timer:
                timer = timer[0]
                self.cancel_timer(timer)
                duration = nice_duration(timer["duration"])
                self.speak_dialog("cancelled.named.timer",
                                  data={"name": timer["name"],
                                        "ordinal": self._get_speakable_ordinal(timer)})
                self.pickle()   # save to disk
            else:
                additional = ''
                names = self._get_speakable_timer_list(self.active_timers)
                which = self.get_response(dialog,
                                            data={"count": num_timers,
                                                "names": names,
                                                "additional": additional})
                if not which:
                    return  # user Cancelled the Cancel

                # Check if they replied "all", "all timers", "both", etc.
                all_words = self.translate_list('all')
                if (which and any(i.strip() in which for i in all_words)):
                    message.data["All"] = all_words[0]
                    self.handle_cancel_timer(message)
                    return

                timer = self._get_timer_matches(which, dialog=dialog)
                if timer:
                    self.cancel_timer(timer)
                    duration = nice_duration(timer["duration"])
                    self.speak_dialog("cancelled.named.timer",
                                    data={"name": timer["name"],
                                            "ordinal": self._get_speakable_ordinal(timer)})
                    self.pickle()   # save to disk
                else:
                    self.speak_dialog("timer.not.found")

        # NOTE: This allows 'ShowTimer' to continue running, it will clean up
        #       after itself nicely.

    def cancel_timer(self, timer):
        # Cancel given timer
        self.log.info("---------CANCEL TIMER---------")
        self.log.info(timer)
        self.log.info("active_timers:")
        for t in self.active_timers:
            self.log.info(t)
        if timer:
            self.active_timers.remove(timer)
            if len(self.active_timers) == 0:
                self.timer_index = 0  # back to zero timers
            self.enclosure.eyes_on()  # reset just in case

    def shutdown(self):
        # Clear the timer list, this fixes issues when stop() gets called
        # on shutdown.
        if len(self.active_timers) > 0:
            active_timers = list(self.active_timers)
            for timer in active_timers:
                self.cancel_timer(timer)

    def converse(self, utterances, lang="en-us"):
        timer = self._get_next_timer()
        if timer and timer["expires"] < datetime.now():
            # A timer is going off
            if utterances and self.voc_match(utterances[0], "StopBeeping"):
                # Stop the timer
                self.stop()
                return True  # and consume this phrase

    # This is a little odd. This actually does the work for the Stop button,
    # which prevents blocking during the Stop handler when input from the
    # user is needed.
    def handle_verify_stop_timer(self, message):
        # Confirm cancel of live timers...
        prompt = ('ask.cancel.running' if len(self.active_timers) == 1
                  else 'ask.cancel.running.plural')
        if self.ask_yesno(prompt) == 'yes':
            self.handle_cancel_timer()

    def stop(self):
        timer = self._get_next_timer()
        now = datetime.now()
        if timer and timer["expires"] < now:
            # stop the expired timer(s)
            while timer and timer["expires"] < now:
                self.cancel_timer(timer)
                timer = self._get_next_timer()
            self.pickle()   # save to disk
            return True

        elif self.active_timers:
            # This is a little tricky.  We shouldn't initiate
            # dialog during Stop handling (there is confusion
            # between stopping speech and starting new conversations).
            # Instead, we'll just consider this Stop consumed and
            # post a message that will immediately be handled to
            # ask the user if they want to cancel.
            self.bus.emit(Message("skill.mycrofttimer.verify.cancel"))
            return True

        return False

    ######################################################################
    # Audio feedback

    def _play_beep(self):
        # Play the beep sound
        if not self._is_playing_beep() and not self.is_listening:
            self.beep_process = play_wav(self.sound_file)

    def _is_playing_beep(self):
        # Check if the WAV is still playing
        if self.beep_process:
            self.beep_process.poll()
            if self.beep_process.returncode:
                # The playback has ended
                self.beep_process = None

    def _stop_beep(self):
        if self._is_playing_beep():
            self.beep_process.kill()
            self.beep_process = None

    ######################################################################
    # TODO:Move to MycroftSkill

    def do_pickle(self, name, data):
        """Serialize the data under the name

        Args:
            name (string): reference name of the pickled data
            data (any): the data to store
        """

        with self.file_system.open(name, 'wb') as f:
            pickle.dump(data, f, pickle.HIGHEST_PROTOCOL)

    def do_unpickle(self, name, default):
        """Load previously saved data under name

        Args:
            name (string): reference name of the pickled data
            default (any): default if data isn't found

        Returns:
            (any): Picked data or the default
        """
        try:
            with self.file_system.open(name, 'rb') as f:
                return pickle.load(f)
        except:
            return default


def create_skill():
    return TimerSkill()
