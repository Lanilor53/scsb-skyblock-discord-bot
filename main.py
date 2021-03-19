import operator
import os
import typing
from datetime import datetime

import discord
import requests
from discord.ext import commands, tasks
from tabulate import tabulate
import matplotlib.pyplot as plt

import database
import itemsrepo

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
    date_string = datetime.utcfromtimestamp(timestamp / 1000).strftime("%Y-%m-%d %H:%M:%S")
    await ctx.send(f'Current ({date_string}) high-demanded items:\n`' + table + '`')


@bot.command()
async def sellgraph(ctx, count: typing.Optional[int] = 5):
    try:
        count = int(count)
    except ValueError or TypeError:
        await ctx.send("Couldn't parse argument")
        return

    if count > 10 or count < 1:
        await ctx.send(f'Argument should be between 1 and 10')
        return

    graph_filename = _get_sell_volume_leaders_graph(count)
    graph = discord.File(graph_filename, filename="graph.png")
    await ctx.send("Here's your graph", file=graph)


@bot.command()
async def sellpricegraph(ctx, count: typing.Optional[int] = 5):
    try:
        count = int(count)
    except ValueError or TypeError:
        await ctx.send("Couldn't parse argument")
        return

    if count > 10 or count < 1:
        await ctx.send(f'Argument should be between 1 and 10')
        return

    graph_filename = _get_sell_price_leaders_graph(count)
    graph = discord.File(graph_filename, filename="graph.png")
    await ctx.send("Here's your graph", file=graph)


# depth-1 crafting income generator
@bot.command()
async def profitablecraft(ctx):
    # TODO: hardcoded for now
    LIMIT = 7
    bazaar_items = database.get_last_products_batch()
    # awful workaround for getByName()
    # TODO: god please rework database
    bazaar_items_dict = {}
    for i in bazaar_items:
        bazaar_items_dict[i.product_id] = i
    profits = {}
    for item in bazaar_items:
        if item.buy_volume == 0 and item.sell_volume == 0:
            continue
        try:
            ingredients = itemsrepo.get_ingredients(item.product_id)
            ingredients_price = 0
            for i in ingredients.keys():
                splitted = i.split(":")

                item_name = splitted[0]
                if len(splitted) > 1:
                    count = int(splitted[1])
                else:
                    count = 1

                ingredients_price += ingredients[i] * count * bazaar_items_dict[item_name].buy_price
            # TODO: maybe use median sell price
            if item.sell_price > ingredients_price:
                profits[item.product_id] = (item.sell_price - ingredients_price,
                                            ingredients)
        except itemsrepo.ItemNotFoundError:
            # print(f"Not found:{item.product_id}")
            continue
        except itemsrepo.NoRecipeError:
            #    print(f"Recipe not found:{item.product_id}")
            continue
        except KeyError:
            continue
    profits_list = []
    for item in profits:
        name = item
        profit = profits[item][0]
        ingredients = profits[item][1]
        profits_list.append([name, profit, ingredients])
    sorted_profits = sorted(profits_list, key=operator.itemgetter(1))
    await ctx.send('`' + tabulate(sorted_profits[:LIMIT:-1], headers=["Name", "Profit", "Ingredients"],
                                  tablefmt="pipe", stralign="left", numalign="left") + '`')


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


def _get_sell_volume_leaders_graph(count):
    # Get all timestamps in DB
    timestamps = list(database.get_all_timestamps("asc"))
    timestamps.sort()
    sell_volumes = {}
    for ts_num in range(len(timestamps)):
        # Get {count} leaders of sell volumes at that time
        leaders = database.get_sorted_batch(database.TimestampedBazaarProduct.sell_volume, "desc", count,
                                            timestamps[ts_num])
        for product in leaders:
            if product.product_id not in sell_volumes.keys():
                sell_volumes[product.product_id] = []
                # Use None as value for all previous timestamps
                for _ in range(ts_num):
                    sell_volumes[product.product_id].append(None)
                sell_volumes[product.product_id].append(product.sell_volume)
            else:
                sell_volumes[product.product_id].append(product.sell_volume)
                print(f"Product {product.product_id} | Sells {sell_volumes[product.product_id]}")
        # Update sell_volume with None where product is not a leader anymore
        for key in sell_volumes.keys():
            if key not in list(i.product_id for i in leaders):
                sell_volumes[key].append(None)
    # Now we have list [timestamps] and [sell_volumes] for every leader at those stamps
    # Plotting
    px = 1 / plt.rcParams['figure.dpi']  # pixel in inches
    fig, ax = plt.subplots(figsize=(1000 * px, 1000 * px))
    for product_id in sell_volumes.keys():
        print(f"Timestamps: {timestamps}")
        print(f"Sells: {sell_volumes[product_id]}")
        ax.plot(list(datetime.utcfromtimestamp(i / 1000) for i in timestamps), sell_volumes[product_id],
                label=product_id)
    ax.set(xlabel='Timestamp', ylabel='Sell volume',
           title='Sell volume leaders by timestamp')
    ax.grid()
    ax.legend()

    fig.savefig("graphs/test.png")
    return "graphs/test.png"


def _get_sell_price_leaders_graph(count):
    # TODO: extract and do "get_leaders_graph(type, count)"
    # Get all timestamps in DB
    timestamps = list(database.get_all_timestamps("asc"))
    timestamps.sort()
    sell_prices = {}
    for ts_num in range(len(timestamps)):
        # Get {count} leaders of sell prices at that time
        leaders = database.get_sorted_batch(database.TimestampedBazaarProduct.sell_price, "desc", count,
                                            timestamps[ts_num])
        for product in leaders:
            if product.product_id not in sell_prices.keys():
                sell_prices[product.product_id] = []
                # Use None as value for all previous timestamps
                for _ in range(ts_num):
                    sell_prices[product.product_id].append(None)
                sell_prices[product.product_id].append(product.sell_volume)
            else:
                sell_prices[product.product_id].append(product.sell_volume)
                print(f"Product {product.product_id} | Sells {sell_prices[product.product_id]}")
        # Update sell_volume with None where product is not a leader anymore
        for key in sell_prices.keys():
            if key not in list(i.product_id for i in leaders):
                sell_prices[key].append(None)
    # Now we have list [timestamps] and [sell_prices] for every leader at those stamps
    # Plotting
    px = 1 / plt.rcParams['figure.dpi']  # pixel in inches
    fig, ax = plt.subplots(figsize=(1000 * px, 1000 * px))
    for product_id in sell_prices.keys():
        print(f"Timestamps: {timestamps}")
        print(f"Sell prices: {sell_prices[product_id]}")
        ax.plot(list(datetime.utcfromtimestamp(i / 1000) for i in timestamps), sell_prices[product_id],
                label=product_id)
    ax.set(xlabel='Timestamp', ylabel='Sell price',
           title='Sell price leaders by timestamp')
    ax.grid()
    ax.legend()

    fig.savefig("graphs/sellprice.png")
    return "graphs/sellprice.png"


def _update_bazaar_data():
    bazaar_data = requests.get(f'{url}/bazaar?key={HYPIXEL_API_KEY}').json()
    database.add_products_batch(bazaar_data)


# Setup and start the bot
# TODO: if highdemand has a volumediff that is < 1 - @everyone with the product
@tasks.loop(minutes=1)
async def do_update():
    # Update SkyBlock's bazaar data
    _update_bazaar_data()

    # Update high demand products message
    message = await bot.get_channel(BOT_CHANNEL_ID).fetch_message(HIGHDEMAND_MESSAGE_ID)
    table, last_timestamp = _get_highdemand_table(10)
    print("Updating pinned highdemand message")
    date_string = datetime.utcfromtimestamp(last_timestamp / 1000).strftime("%Y-%m-%d %H:%M:%S")
    await message.edit(content=f'Current high-demanded items (updated on {date_string}' + '\n`' + table + '`',
                       suppress=True)


@bot.event
async def on_ready():
    do_update.start()
    print('GO GO GO')


bot.run(DISCORD_TOKEN)
