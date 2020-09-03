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

import requests
import json
import board
import busio
import adafruit_character_lcd.character_lcd_rgb_i2c as character_lcd

from os.path import join, isfile, abspath, dirname
#from num2words import num2words
from adapt.intent import IntentBuilder
from mycroft.audio import wait_while_speaking
from mycroft.messagebus.message import Message
from mycroft.skills.core import (
    MycroftSkill,
    intent_handler,
    intent_file_handler)
from mycroft.util import play_wav
from mycroft.util.format import pronounce_number, join_list
from mycroft.util.parse import extract_number

class PokemonNumSkill(MycroftSkill):
    
    def __init__(self):
        super(PokemonNumSkill, self).__init__("PokemonNumSkill")
        #self.sound_file = join(abspath(dirname(__file__)), 'snd','twoBeep.wav')
        #self.threshold = 0.7
        lcd_columns = 16
        lcd_rows = 2
        i2c = busio.I2C(board.SCL, board.SDA)
        lcd = character_lcd.Character_LCD_RGB_I2C(i2c, lcd_columns, lcd_rows)
        lcd.color = [55, 0, 55]
        lcd.message = "Hello\nCircuitPython"
    
    def initialize(self):
        for i in range(800):  # numbers 0 to 100
            self.register_vocabulary(str(i), 'Numz')
        # To prevent beeping while listening
        #lcd.color = [55, 0, 55]
        #lcd.message = "Hello\nCircuitPython"
      
    ######################################################################
    # INTENT HANDLERS

    @intent_handler(IntentBuilder("PokemonNumber").require("Pokemon")
                    .optionally("Number")
                    .require("Numz"))
    def handle_pokemon_number(self, message):
        """Tells the user what it's searching for"""
        num = extract_number(message.data['utterance'])
        #lcd.message = num
        self.speak_dialog('list.pokemon.number', data={'level': num})             

        #Tells the user the Pokemon
        resp = requests.get("https://pokeapi.co/api/v2/pokemon-form/"+str(num)+"/")
        #print(response.status_code)
        #jprint(response.json())
        nme=resp.json()['name']
        #pokemon_name=self.__jprint(self, nme)
        pokemon_name=json.dumps(nme, sort_keys=True, indent=4)
        #pokemon_name=pokemon_name.strip('\"')
        self.speak_dialog('list.pokemon.name', data={"title": pokemon_name})

        #Get the Pokemon Type
        response = requests.get("https://pokeapi.co/api/v2/pokemon/"+str(num)+"/")
        types=response.json()["types"]
        ttyp=[]
        typ=[]
        #gets the details of all the types in ttyp list
        for d in types:
            temp=d["type"]
            ttyp.append(temp)
        #gets the names of the types in typ list.
        for d in ttyp:
            temp=d["name"]
            typ.append(temp)

        pokemon_type=""
        for i in range(0,len(typ)): 
            pokemon_type=pokemon_type + typ[i] + " and "
        pokemon_type = pokemon_type[:-5] + " Type"
        self.speak_dialog('list.pokemon.type', data={"typee": pokemon_type})   
        
        #Get the Pokemon Description
        response = requests.get("https://pokeapi.co/api/v2/pokemon-species/"+str(num)+"/")
        descriptions=response.json()["flavor_text_entries"]
        descripts= []
        for d in descriptions:
            temp = d["flavor_text"]
            descripts.append(temp)
        pokemon_description = str(descripts[0])
        self.speak_dialog('list.pokemon.description', data={"desc": pokemon_description})
                
        #self.speak_dialog(dialog,n})
        # Start showing the remaining time on the faceplate
    # Handles custom start phrases eg "ping me in 5 minutes"
    # Also over matches Common Play for "start timer" utterances
    #def __jprint(self, obj):
    #    # create a formatted string of the Python JSON object
    #    text = json.dumps(obj, sort_keys=True, indent=4)
    #    #print(text)
    #    return text 
    
    def stop(self):
        pass

def create_skill():
    return PokemonNumSkill()
