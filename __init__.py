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

#lcd_columns = 16
#lcd_rows = 2
#i2c = busio.I2C(board.SCL, board.SDA)
#lcd = character_lcd.Character_LCD_RGB_I2C(i2c, lcd_columns, lcd_rows)
#lcd.color = [55, 0, 55]
#lcd.message = "Hello\nCircuitPython"


class PokemonNumSkill(MycroftSkill):
 
    def __init__(self):
        super(PokemonNumSkill, self).__init__("PokemonNumSkill")
        #self.sound_file = join(abspath(dirname(__file__)), 'snd','twoBeep.wav')
        #self.threshold = 0.7
      
    
    def initialize(self):
        for i in range(808):  # numbers 0 to 100
            self.register_vocabulary(str(i), 'Numz')
        response = requests.get("http://pokeapi.co/api/v2/pokemon?limit=807")
        names=response.json()["results"]
        for d in names:
        #This bit gets ALL the pokemon names.
            self.register_vocabulary(str(d['name']), 'Namez')
        #This will try matching to the string and print out the Pokeindex
    
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
        global lcd
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
        #lcd.message = '\nPokemon:' + str(num) 
        lcd_columns = 16
        lcd_rows = 2
        i2c = busio.I2C(board.SCL, board.SDA)
        lcd = character_lcd.Character_LCD_RGB_I2C(i2c, lcd_columns, lcd_rows)
        lcd.color = [100, 0, 0]
        lcd.message = "\nPokemon:" + str(num)
        lcd.message = str(pokemon_name).strip('\"')
        
 #       update_display(num,pokemon_name)
    
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
        pokemon_description = str(descripts[14])
        self.speak_dialog('list.pokemon.description', data={"desc": pokemon_description})
        
        # Configuration for CS and DC pins (these are PiTFT defaults):
        cs_pin = digitalio.DigitalInOut(board.CE0)
        dc_pin = digitalio.DigitalInOut(board.D17)
        reset_pin = digitalio.DigitalInOut(board.D4)

        # Config for display baudrate (default max is 24mhz):
        BAUDRATE = 24000000

        # Setup SPI bus using hardware SPI:
        spi = board.SPI()

        # pylint: disable=line-too-long
        # Create the display:

        disp = st7735.ST7735R(
            spi, 
            rotation=270, 
            height=128, 
            x_offset=2, 
            y_offset=3,
            cs=cs_pin,
            dc=dc_pin,
            rst=reset_pin,
            baudrate=BAUDRATE,
        )
        # pylint: enable=line-too-long
        
        # Create blank image for drawing.
        # Make sure to create image with mode 'RGB' for full color.
        if disp.rotation % 180 == 90:
            height = disp.width  # we swap height/width to rotate it to landscape!
            width = disp.height
        else:
            width = disp.width  # we swap height/width to rotate it to landscape!
            height = disp.height
        image = Image.new("RGB", (width, height))
        
        # Get drawing object to draw on image.
        draw = ImageDraw.Draw(image)
        
        # Draw a black filled box to clear the image.
        draw.rectangle((0, 0, width, height), outline=0, fill=(0, 0, 0))
        disp.image(image)
        
        #image = Image.open("blinka.jpg")
        url= 'https://pokeres.bastionbot.org/images/pokemon/'+str(num)+'.png'
        myfile = requests.get(url)
        open ('temp.png','wb').write(myfile.content)
        image = Image.open('temp.png')
        
        # Scale the image to the smaller screen dimension
        image_ratio = image.width / image.height
        screen_ratio = width / height
        if screen_ratio < image_ratio:
            scaled_width = image.width * height // image.height
            scaled_height = height
        else:
            scaled_width = width
            scaled_height = image.height * width // image.width
        image = image.resize((scaled_width, scaled_height), Image.BICUBIC)
        
        # Crop and center the image
        x = scaled_width // 2 - width // 2
        y = scaled_height // 2 - height // 2
        image = image.crop((x, y, x + width, y + height))
        
        # Display image.
        disp.image(image)

              
        
        #self.speak_dialog(dialog,n})
        # Start showing the remaining time on the faceplate
    # Handles custom start phrases eg "ping me in 5 minutes"
    # Also over matches Common Play for "start timer" utterances
    #def __jprint(self, obj):
    #    # create a formatted string of the Python JSON object
    #    text = json.dumps(obj, sort_keys=True, indent=4)
    #    #print(text)
    #    return text 

    @intent_handler(IntentBuilder("PokemonName").require("Pokemon")
                    .require("Namez"))
    def handle_pokemon_name(self, message):
        """Tells the user what it's searching for"""
        nme_str = message.data.get('Namez')
        #nme = (message.data['utterance'])
        #lcd.message = num
        self.speak_dialog('list.pokemon.number', data={'level': nme_str})             
        response = requests.get("http://pokeapi.co/api/v2/pokemon?limit=807")
        names=response.json()["results"]
        #print (d)
        for d in names:
            if str(d['name']) == nme_str:
                #self.speak('Found it')
            #if str(d['name']) == str(nme):
                temp=str(d['url']).split("/")
                self.speak_dialog('list.pokemon.number', data={'level': temp[6]})
    
    
    def update_disply(num,pokemon_name):
        lcd_columns = 16
        lcd_rows = 2
        i2c = busio.I2C(board.SCL, board.SDA)
        lcd = character_lcd.Character_LCD_RGB_I2C(i2c, lcd_columns, lcd_rows)
        lcd.color = [100, 0, 0]
        lcd.message = "\nPokemon:" + str(num)
        lcd.message = str(pokemon_name).strip('\"')
    
    def stop(self):
        pass

def create_skill():
    return PokemonNumSkill()
