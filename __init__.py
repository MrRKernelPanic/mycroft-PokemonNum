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

import digitalio
from PIL import Image, ImageDraw
import adafruit_rgb_display.st7735 as st7735  # pylint: disable=unused-import
import requests


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
        self.pokemon_name = ""
        self.pokemon_number = 0
        self.pokemon_description = ""
        self.pokemon_type = ""
        self.pokemon_image = ""
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.lcd = character_lcd.Character_LCD_RGB_I2C(self.i2c, 16, 2)
    
    def initialize(self):
        for i in range(808):  # numbers 0 to 100
            self.register_vocabulary(str(i), 'Numz')
        response = requests.get("http://pokeapi.co/api/v2/pokemon?limit=807")
        names=response.json()["results"]
        for d in names:
        #This bit gets ALL the pokemon names.
            self.register_vocabulary(str(d['name']), 'Namez')
        #This will try matching to the string and print out the Pokeindex
        
    #This is not working yet.  
    #def update_disply(self, num, pokemon_name):
    #    lcd_columns = 16
    #    lcd_rows = 2
    #    i2c = busio.I2C(board.SCL, board.SDA)
    #    lcd = character_lcd.Character_LCD_RGB_I2C(i2c, lcd_columns, lcd_rows)
    #    lcd.color = [100, 0, 0]
    #    lcd.message = "\nPokemon:" + str(num)
    #    lcd.message = str(pokemon_name).strip('\"')
    
    ######################################################################
    # INTENT HANDLERS

    @intent_handler(IntentBuilder("PokemonNumber").require("Pokemon")
                    .optionally("Number")
                    .require("Numz"))
    def handle_pokemon_number(self, message):
        """Tells the user what it's searching for"""
        self.pokemon_number = extract_number(message.data['utterance'])
        self.speak_dialog('list.pokemon.number', data={'level': self.pokemon_number})             
        wait_while_speaking()
      
        #Tells the user the Pokemon
        resp = requests.get("https://pokeapi.co/api/v2/pokemon-form/"+str(self.pokemon_number)+"/")
        #print(response.status_code)
        #jprint(response.json())
        nme=resp.json()['name']
        #pokemon_name=self.__jprint(self, nme)
        self.pokemon_name=json.dumps(nme, sort_keys=True, indent=4)
        #self.pokemon_name = pname
        #pokemon_name=pokemon_name.strip('\"')
        self.speak_dialog('list.pokemon.name', data={"title": str(self.pokemon_name)})
        #lcd_columns = 16
        #lcd_rows = 2
        #i2c = busio.I2C(board.SCL, board.SDA)
        #lcd = character_lcd.Character_LCD_RGB_I2C(i2c, lcd_columns, lcd_rows)
        self.lcd.color = [100, 0, 0]
        self.lcd.message = "\nPokemon:" + str(self.pokemon_number)
        self.lcd.message = str(self.pokemon_name).strip('\"')   

#       update_display(num,pokemon_name)
        #Get the Pokemon Type
        response = requests.get("https://pokeapi.co/api/v2/pokemon/"+str(self.pokemon_number)+"/")
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
        
        for i in range(0,len(typ)): 
            ptype=ptype + typ[i] + " and "       
        self.pokemon_type = = ptype[:-5] + " Type"
        wait_while_speaking()
        self.speak_dialog('list.pokemon.type', data={"typee": str(self.pokemon_type)}) 
    
    def stop(self):
        pass

def create_skill():
    return PokemonNumSkill()
