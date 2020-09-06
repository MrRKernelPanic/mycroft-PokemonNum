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
        self.pokemon_name = ""
        self.pokemon_number = 0
        self.pokemon_description = ""
        self.pokemon_type = ""
        self.pokemon_image = ""
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.lcd = character_lcd.Character_LCD_RGB_I2C(self.i2c, 16, 2)
        self.lcd.clear()
        
         # Configuration for CS and DC pins (these are PiTFT defaults):
        self.cs_pin = digitalio.DigitalInOut(board.CE0)
        self.dc_pin = digitalio.DigitalInOut(board.D17)
        self.reset_pin = digitalio.DigitalInOut(board.D4)

        # Config for display baudrate (default max is 24mhz):
        self.BAUDRATE = 24000000

        # Setup SPI bus using hardware SPI:
        self.spi = board.SPI()

        # pylint: disable=line-too-long
        # Create the display:

        self.disp = st7735.ST7735R(
            self.spi, 
            rotation=270, 
            height=128, 
            x_offset=2, 
            y_offset=3,
            cs=self.cs_pin,
            dc=self.dc_pin,
            rst=self.reset_pin,
            baudrate=self.BAUDRATE,
        )
        
        # Make sure to create image with mode 'RGB' for full color.
        if self.disp.rotation % 180 == 90:
            self.height = self.disp.width  # we swap height/width to rotate it to landscape!
            self.width = self.disp.height
        else:
            self.width = self.disp.width  # we swap height/width to rotate it to landscape!
            self.height = self.disp.height
        self.image = Image.new("RGB", (self.width, self.height))
        
        # Get drawing object to draw on image.
        draw = ImageDraw.Draw(self.image)
        
        # Draw a black filled box to clear the image.
        draw.rectangle((0, 0, self.width, self.height), outline=0, fill=(0, 0, 0))
        self.disp.image(self.image)
        
        
    
    def initialize(self):
        for i in range(808):  # numbers 0 to 100
            self.register_vocabulary(str(i), 'Numz')
        response = requests.get("http://pokeapi.co/api/v2/pokemon?limit=807")
        names=response.json()["results"]
        for d in names:
        #This bit gets ALL the pokemon names.
            self.register_vocabulary(str(d['name']), 'Namez')
        #This will try matching to the string and print out the Pokeindex
    
    def get_pokemon_name(self):
        #Tells the user the Pokemon
        resp = requests.get("https://pokeapi.co/api/v2/pokemon-form/"+str(self.pokemon_number)+"/")
        nme=resp.json()['name']
        self.pokemon_name=json.dumps(nme, sort_keys=True, indent=4)
        self.speak_dialog('list.pokemon.name', data={"title": self.pokemon_name})
        self.lcd.color = [100, 0, 0]
        self.lcd.message = "\nPokemon:" + str(self.pokemon_number)
        self.lcd.message = str(self.pokemon_name).strip('\"')   

#       update_display(num,pokemon_name)
    def get_pokemon_type(self):
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
            self.pokemon_type=self.pokemon_type + str(typ[i]) + " and "       
        self.pokemon_type= self.pokemon_type[:-5] + " Type"
        wait_while_speaking()
        self.speak_dialog('list.pokemon.type', data={"typee": self.pokemon_type}) 
        
        #Get the Pokemon Description

    def get_pdescription_en(self):
        response = requests.get("https://pokeapi.co/api/v2/pokemon-species/"+str(self.pokemon_number)+"/")
        descriptions=response.json()["flavor_text_entries"]
        for descriptions_data in descriptions:
            descr=descriptions_data["flavor_text"]
            region = descriptions_data["language"]
            if 'en' in str(region):
#               print (str(region))
#               print (str(descr))
                self.pokemon_description =str(descr)
                wait_while_speaking()
                self.speak_dialog('list.pokemon.description', data={"desc": self.pokemon_description})
                return    

    def get_pimage(self):
        self.pokemon_image = 'https://pokeres.bastionbot.org/images/pokemon/'+str(self.pokemon_number)+'.png'
        myfile = requests.get(self.pokemon_image)
        open('temp.png','wb').write(myfile.content)
        image = Image.open('temp.png')
        
        # Scale the image to the smaller screen dimension
        image_ratio = image.width / image.height
        screen_ratio = self.width / self.height
        if screen_ratio < image_ratio:
            scaled_width = image.width * self.height // image.height
            scaled_height = self.height
        else:
            scaled_width = self.width
            scaled_height = image.height * self.width // image.width
        image = image.resize((scaled_width, scaled_height), Image.BICUBIC)
        
        # Crop and center the image
        x = scaled_width // 2 - self.width // 2
        y = scaled_height // 2 - self.height // 2
        image = image.crop((x, y, x + self.width, y + self.height))
        # Display image.
        self.disp.image(image)
    
    
    
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
        self.get_pokemon_name()
        self.get_pokemon_type()
        self.get_pdescription_en()
        self.get_pimage()
           
    def stop(self):
        pass

def create_skill():
    return PokemonNumSkill()
