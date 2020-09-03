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

import re
import board
import busio
import adafruit_character_lcd.character_lcd_rgb_i2c as character_lcd

from os.path import join, isfile, abspath, dirname
from num2words import num2words
from adapt.intent import IntentBuilder
from mycroft.audio import wait_while_speaking, is_speaking
from mycroft.messagebus.message import Message
from mycroft.skills.core import (
    MycroftSkill,
    intent_handler,
    intent_file_handler)
from mycroft.util import play_wav
from mycroft.util.format import pronounce_number, join_list
from mycroft.util.parse import extract_number, fuzzy_match
from mycroft.util.time import now_local

try:
    from mycroft.skills.skill_data import to_alnum
except ImportError:
    from mycroft.skills.skill_data import to_letters as to_alnum

from .util.bus import wait_for_message

class PokemonNumSkill(MycroftSkill):
    def __init__(self):
        super(PokemonNumSkill, self).__init__("PokemonNumSkill")
        #self.sound_file = join(abspath(dirname(__file__)), 'snd','twoBeep.wav')
        self.threshold = 0.7

    def initialize(self):
        # To prevent beeping while listening
        lcd_columns = 16
        lcd_rows = 2
        i2c = busio.I2C(board.SCL, board.SDA)
        lcd = character_lcd.Character_LCD_RGB_I2C(i2c, lcd_columns, lcd_rows)
        lcd.color = [55, 0, 55]
        lcd.message = "Hello\nCircuitPython"

    def _extract_ordinal(self, text):
        """Extract ordinal from text.

        Remove once extract_number supports short ordinal format eg '2nd'
        """
        num = None
        if text is None or len(text) == 0:
            return None

        try:
            num = extract_number(text, self.lang, ordinals=True)
            # attempt to remove extracted ordinal
            spoken_ord = num2words(int(num), to="ordinal", lang=self.lang)
            utt = text.replace(spoken_ord,"")
        except:
            self.log.debug('_extract_ordinal: Error in extract_number method')
            pass
        if not num:
            try:
                # Should be removed if the extract_number() function can
                # parse ordinals already e.g. 1st, 3rd, 69th, etc.
                regex = re.compile(r'\b((?P<Numeral>\d+)(st|nd|rd|th))\b')
                result = re.search(regex, text)
                if result and (result['Numeral']):
                    num = result['Numeral']
                    utt = text.replace(result, "")
            except:
                self.log.debug('_extract_ordinal: Error in regex search')
                pass
        return int(num), utt

    @staticmethod
    def _fuzzy_match_word_from_phrase(word, phrase, threshold):
        matched = False
        score = 0
        phrase_split = phrase.split(' ')
        word_split_len = len(word.split(' '))

        for i in range(len(phrase_split) - word_split_len, -1, -1):
            phrase_comp = ' '.join(phrase_split[i:i + word_split_len])
            score_curr = fuzzy_match(phrase_comp, word.lower())

            if score_curr > score and score_curr >= threshold:
                score = score_curr
                matched = True

        return matched

    
    ######################################################################
    # INTENT HANDLERS

    @intent_handler(IntentBuilder("pokemon.number").require("Pokemon").require("Number")
    def handle_pokemon_number(self, message):
        """Common handler for start_timer intents."""
        num = extract_number(message.data['utterance'])
        lcd.message = num
        #self.speak_dialog(dialog,n})
        # Start showing the remaining time on the faceplate
                    
    # Handles custom start phrases eg "ping me in 5 minutes"
    # Also over matches Common Play for "start timer" utterances
 
    def stop(self):
        pass

def create_skill():
    return PokemonNumSkill()
