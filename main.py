import discord
import requests
import requests_cache
from discord.ext import commands, tasks
from tabulate import tabulate
import typing
import time
import json
import os

DISCORD_TOKEN = os.environ.get("discord_token")
HYPIXEL_API_KEY = os.environ.get("hypixel_api_key")

BOT_CHANNEL_ID = int(os.environ.get("bot_channel_id"))
HIGHDEMAND_MESSAGE_ID = int(os.environ.get("highdemand_pin_id"))

url = "https://api.hypixel.net/skyblock"
bot = commands.Bot(command_prefix ="!")

@bot.command()
async def highdemand(ctx, count: typing.Optional[int] = 10):
  try:
    count = int(count)
  except:
    await ctx.send("Couldn't parse argument")
    return

  if count > 10 or count < 1:
    await ctx.send(f'Argument should be between 1 and 10')
    return
  
  table = _get_highdemand(count)  
  await ctx.send('Current high-demanded items:\n`' + table + '`')

def _get_highdemand(count):
  db = requests.get(f'{url}/bazaar?key={HYPIXEL_API_KEY}').json()['products']
  volume_diffs = {}
  for item in db.keys():
      if (db[item]["quick_status"]["buyVolume"]== 0 and db[item]["quick_status"]["sellVolume"] == 0):
        continue
      volume_diff = db[item]["quick_status"]["buyVolume"]-db[item]["quick_status"]["sellVolume"]
      volume_diffs[item] = volume_diff
  # Generate top 5 #TODO: 5 should be modifiable
  top = {}
  top_list = []
  for i in range(count):
    max_diff = -999999999
    max_item = ""
    # Find max diff
    for key in volume_diffs.keys():
        if volume_diffs[key] > max_diff:
            max_item = key
            max_diff = volume_diffs[key]
    maxItem_sell_volume = db[max_item]['quick_status']['sellVolume']
    maxItem_buy_volume = db[max_item]['quick_status']['buyVolume']
    maxItem_buy_price = db[max_item]['quick_status']['buyPrice']
    maxItem_sell_price = db[max_item]['quick_status']['sellPrice']
    maxItem_price_diff = maxItem_buy_price - maxItem_sell_price
    top_list.append([max_item, maxItem_sell_volume, maxItem_buy_volume, max_diff, maxItem_buy_price, maxItem_sell_price, maxItem_price_diff])
    volume_diffs.pop(max_item)
 
  return tabulate(top_list, headers=["Name", "Sell volume", "Buy volume", "Volume diff", "Buy price", "Sell price", "Price diff"], tablefmt="pipe", stralign="left", numalign="left")

@tasks.loop(minutes=3)
async def update_highdemand_message():
    message = await bot.get_channel(BOT_CHANNEL_ID).fetch_message(HIGHDEMAND_MESSAGE_ID)
    table = _get_highdemand(10)
    print("Updating pinned highdemand message")
    await message.edit(content=f'Current high-demanded items (updated on {time.ctime()}):\n`' + table + '`',suppress=True)

@bot.event
async def on_ready():
    update_highdemand_message.start()
    print('GOGOGO')

bot.run(DISCORD_TOKEN)