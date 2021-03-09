import os
import typing
from datetime import datetime

import requests
from discord.ext import commands, tasks
from tabulate import tabulate

import database

# Setting up constants
DISCORD_TOKEN = os.environ.get("discord_token")
HYPIXEL_API_KEY = os.environ.get("hypixel_api_key")

BOT_CHANNEL_ID = int(os.environ.get("bot_channel_id"))
HIGHDEMAND_MESSAGE_ID = int(os.environ.get("highdemand_pin_id"))

url = "https://api.hypixel.net/skyblock"
bot = commands.Bot(command_prefix="!")


# Get highdemanded items on the market
@bot.command()
async def highdemand(ctx, count: typing.Optional[int] = 10):
    try:
        count = int(count)
    except ValueError or TypeError:
        await ctx.send("Couldn't parse argument")
        return

    if count > 10 or count < 1:
        await ctx.send(f'Argument should be between 1 and 10')
        return

    table, timestamp = _get_highdemand_table(count)
    date_string = datetime.utcfromtimestamp(timestamp/1000).strftime("%Y-%m-%d %H:%M:%S")
    await ctx.send(f'Current ({date_string}) high-demanded items:\n`' + table + '`')


def _get_highdemand_table(count):
    products_object = database.get_last_products_batch()
    last_timestamp = products_object[0].timestamp

    volume_diffs = {}
    for item in products_object:
        if item.buy_volume == 0 and item.sell_volume == 0:
            continue
        volume_diff = item.buy_volume - item.sell_volume
        volume_diffs[item] = volume_diff
    # Generate top list
    top_list = []
    for i in range(count):
        max_diff = -999999999
        max_item = ""
        # Find max diff
        for key in volume_diffs.keys():
            if volume_diffs[key] > max_diff:
                max_item = key
                max_diff = volume_diffs[key]
        max_item_sell_volume = max_item.sell_volume
        max_item_buy_volume = max_item.buy_volume
        max_item_buy_price = max_item.buy_price
        max_item_sell_price = max_item.sell_price
        max_item_price_diff = max_item_buy_price - max_item_sell_price
        top_list.append(
            [max_item.product_id, max_item_sell_volume, max_item_buy_volume, max_diff, max_item_buy_price,
             max_item_sell_price,
             max_item_price_diff])
        volume_diffs.pop(max_item)

    return tabulate(top_list, headers=["Name", "Sell volume", "Buy volume", "Volume diff", "Buy price", "Sell price",
                                       "Price diff"], tablefmt="pipe", stralign="left", numalign="left"), last_timestamp


def _update_bazaar_data():
    bazaar_data = requests.get(f'{url}/bazaar?key={HYPIXEL_API_KEY}').json()
    database.add_products_batch(bazaar_data)


# Setup and start the bot
# TODO: if highdemand has a volumediff that is < 1 - @everyone with the product
@tasks.loop(minutes=5)
async def do_update():
    # Update SkyBlock's bazaar data
    _update_bazaar_data()
    # Update high demand products message
    message = await bot.get_channel(BOT_CHANNEL_ID).fetch_message(HIGHDEMAND_MESSAGE_ID)
    table, last_timestamp = _get_highdemand_table(10)
    print("Updating pinned highdemand message")
    date_string = datetime.utcfromtimestamp(last_timestamp/1000).strftime("%Y-%m-%d %H:%M:%S")
    await message.edit(content=f'Current high-demanded items (updated on {date_string}' + '\n`' + table + '`',
                       suppress=True)


@bot.event
async def on_ready():
    do_update.start()
    print('GO GO GO')


bot.run(DISCORD_TOKEN)
