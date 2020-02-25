Feature: mycroft-timer

  Scenario Outline: start a timer for a specified duration
    Given an english speaking user
      When the user says "<start a timer for a specified duration>"
      Then "mycroft-timer" should reply with dialog from "started.timer.dialog"

   Examples: start a timer for for a specified duration
     | start a timer for a specified duration |
     | timer 10 minutes |
     | timer 30 seconds |
     | set a timer for 5 minutes |
     | start a 1 minute timer |
     | start a timer for 1 minute and 30 seconds |
     | begin timer 2 minutes |
     | create a timer for 1 hour |
     | create a timer for 1 hour and 30 minutes |
     | ping me in 5 minutes |

  Scenario Outline: start another timer for for a specified duration
    Given an english speaking user
      And there is already an active timer
      When the user says "<start another timer for for a specified duration>"
      Then "mycroft-timer" should reply with dialog from "started.timer.dialog"

   Examples: start another timer
     | start another timer for for a specified duration |
     | second timer 20 minutes |
     | start another timer for 5 minutes |
     | set one more timer for 10 minutes |
     | set a timer for 2 minutes |

  Scenario Outline: start a named timer for for a specified duration
    Given an English speaking user
       When the user says "<start a named timer for a specified duration>"
       Then "mycroft-timer" should reply with dialog from "started.timer.with.name.dialog"

   Examples: start a named timer for a specified duration
     | start a named timer for a specified duration |
     | set a 10 minute timer for pasta |
     | set a timer for 10 minutes for pasta |
     | start a timer for 25 minutes called oven one |
     | start a timer for 15 minutes named oven two |

  Scenario Outline: start a timer for an unspecified duration
    Given an english speaking user
      When the user says "<start a timer for an unspecified duration>"
      Then "mycroft-timer" should reply with "ask.how.long.dialog"
      And the user replies with "5 minutes"
      And "mycroft-timer" should reply with dialog from "started.timer.dialog"

   Examples: start a timer for an unspecified duration
     | start a timer for an unspecified duration |
     | timer |
     | set a timer |
     | start a timer |
     | timer for 5 |

  Scenario Outline: start another timer for an unspecified duration
    Given an english speaking user
      And there is already an active timer
      When the user says "<start another timer for an unspecified duration>"
      Then "mycroft-timer" should reply with dialog from "ask.how.long.dialog"
      And the user replies with "5 minutes"
      And "mycroft-timer" should reply with dialog from "started.timer.dialog"

   Examples: start another timer for an unspecified duration
     | set another timer for an unspecified duration |
     | start another timer |
     | one more timer |
     | second timer |

  Scenario Outline: start a named timer for an unspecified duration
    Given an english speaking user
      When the user says "<start a named timer>"
      Then "mycroft-timer" should reply with dialog from "ask.how.long.dialog"
      And the user replies with "5 minutes"
      And "mycroft-timer" should reply with dialog from "started.timer.with.name.dialog"

   Examples: start a named timer for an unspecified duration
     | start a named timer for an unspecified duration |
     | set a timer named pasta |
     | set a timer for pasta |
     | start a timer named pasta |
     | start a timer for pasta |

  Scenario Outline: cancel timer with one active timer
    Given an english speaking user
      And only one timer is set
      When the user says "<cancel timer with one active timer>"
      Then "mycroft-timer" should reply with dialog from "cancelled.single.timer.dialog"

   Examples: cancel timer with one active timer
     | cancel timer with one active timer |
     | stop the timer |
     | end timer |
     | end the timer |
     | kill the timer |
     | disable timer |
     | disable the timer |
     | delete timer |
     | remove timer |

  Scenario Outline: cancel timer with two active timers
    Given an english speaking user
      And a 1 minute timer is set
      And a 2 minute timer is set
      When the user says "<cancel timer with no active timers>"
      Then "mycroft-timer" should reply with dialog from "ask.which.timer.cancel.dialog"
      And the user replies "1 minute"
      And "mycroft-timer" should reply with dialog from "cancelled.single.timer.dialog"

   Examples: cancel timer with two active timer
     | cancel timer with two active timers |
     | stop the timer |
     | end timer |
     | end the timer |
     | kill the timer |
     | disable timer |
     | disable the timer |
     | delete timer |
     | remove timer |

  Scenario Outline: cancel timer with three active timers
    Given an english speaking user
      And a 1 minute timer is set
      And a 2 minute timer is set
      And a 3 minute timer is set
      When the user says "<cancel timer with three active timers>"
      Then "mycroft-timer" should reply with dialog from "ask.which.timer.dialog"
      And the user replies "1 minute"
      And "mycroft-timer" should reply with dialog from "cancelled.single.timer.dialog"

   Examples: cancel timer with three active timer
     | cancel timer with three active timers |
     | cancel timer |
     | stop the timer |
     | end timer |
     | end the timer |
     | kill the timer |
     | disable timer |
     | disable the timer |
     | delete timer |
     | remove timer |

  Scenario Outline: cancel timer with no timer active
    Given an english speaking user
      And no timers are active
      When the user says "<cancel timer with no timer active>"
      THen "mycroft-timer" should reply with dialog from "no.active.timer.dialog"

   Examples: cancel timer with no timer active
     | cancel timer with no timer active |
     | cancel timer |
     | stop the timer |
     | end timer |
     | end the timer |
     | kill the timer |
     | disable timer |
     | disable the timer |
     | delete timer |
     | remove timer |


  Scenario Outline: cancel a specific timer
    Given an english speaking user
      And a 5 minute timer is set
      And a 10 minute timer is set
      When the user says "<cancel a specific timer>"
      Then "mycroft-timer" should reply with dialog from "cancelled.timer.named.dialog"

   Examples: cancel a specific timer
     | cancel a specific timer |
     | stop the 5 minute timer |
     | cancel the 5 minute timer |
     | end 5 minute timer |
     | end the 5 minute timer |
     | kill the 5 minute timer |
     | disable 5 minute timer |
     | disable the 5 minute timer |
     | delete the 5 minute timer |
     | remove the 5 minute timer |

  Scenario Outline: cancel a named timer
    Given an english speaking user
      And a timer named pasta is set
      When the user says "<cancel pasta timer>"
      Then "mycroft-timer" should reply with dialog from "cancelled.timer.named.dialog"

   Examples: cancel a named timer
     | cancel pasta timer |
     | stop the pasta timer |
     | end pasta timer |
     | end the pasta timer |
     | kill the pasta timer |
     | disable pasta timer |
     | disable the pasta timer |
     | delete the pasta timer |
     | remove pasta timer |


  Scenario Outline: cancel all timers when 3 timers are active
    Given an english speaking user
      And a timer is set for 5 minutes
      And a timer is set for 10 minutes
      And a timer is set for 15 minutes
      When the user says "<cancel all timers>"
      Then "mycroft-timer" should reply with dialog from "cancel.all.dialog"

   Examples: cancel all timers
     | cancel all timers |
     | delete all timers |
     | remove all timers |
     | stop all timers |
     | kill all timers |
     | disable all timers |
     | turn off all timers |

  Scenario Outline: stop an expired timer from beeping
    Given an english speaking user
      And a timer is expired
      When the user says "<stop timer>"
      Then "mycroft-timer" should stop beeping

   Examples: stop timer
     | stop timer |
     | stop timer |
     | stop |
     | cancel |
     | end timer |
     | turn it off |
     | silence |
     | I got it |
     | mute |
     | shut up |
     | cancel all timers |
     | cancel the timers |
     | cancel timers |
     | disable |
     | that's enough |

  Scenario Outline: status of a single timer
    Given an english speaking user
      And a timer is set for 5 minutes
      When the user says "<status of a single timer>"
      Then "mycroft-timer" should reply with dialog from "time.remaining.dialog"

   Examples: status of a single timer
     | status of a single timer |
     | timer status |
     | what's left on my timer |
     | how much is left on the timer |
     | what's the remaining time |
     | how's my timer |
     | do I have any timers |
     | are there any timers |
     | what timers do I have |
     | when does the timer end |

  Scenario Outline: status when there are no active timers
    Given an english speaking user
      And no timers are set
      When the user says "<status when there are no active timers>"
      Then "mycroft-timer" should reply with dialog from "no.active.timer.dialog"

   Examples: status when there are no active timers
     | status when there are no active timers |
     | timer status |
     | what's left on my timer |
     | how much is left on the timer |
     | what's the remaining time |
     | how's my timer |
     | do I have any timers |
     | are there any timers |
     | what timers do I have |
     | when does the timer end |

  Scenario Outline: status of named timer
    Given an english speaking user
      And a timer named chicken is set for 20 minutes
      When the user says "<what is the status of named timer>"
      Then "mycroft-timer" should reply with dialog from "time.remaining.named.dialog"

  Examples: status of named timer
     | what is the status of name timer |
     | what is the status of the chicken timer |


  Scenario Outline: status of two timers
    Given an english speaking user
      And a 5 minute timer is set
      And a 10 minute timer is set
      When the user says "<status of two timers>"
      Then "mycroft-timer" should reply with dialog from "number.of.timers.dialog"
      And "mycroft-timer" should reply with dialog from "time.remaining.dialog"
      And "mycroft-timer" should reply with dialog from "time.remaining.dialog"

  Examples: status of named timer
     | status of two timers |
     | what's the status of the timers |
     | what's left on my timers |
     | how much time is left on the timers |
     | what's the remaining time |
     | how's my timer |
     | do I have any timers |
     | are there any timers |
     | what timers do I have |
     | when does the timer end |
