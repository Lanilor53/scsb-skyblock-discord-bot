import logging
import operator
import os
import typing
from datetime import datetime

import discord
import matplotlib.pyplot as plt
import requests
from discord.ext import commands, tasks
from tabulate import tabulate

import database
import items

# Set up logging
log = logging.getLogger("main")
logging.basicConfig(format="%(name)-30s %(levelname)-8s %(message)s",
                    level=logging.INFO,
                    filename="scsb-skyblock-bot.log")

# Set up tabulate
TABLEFMT = "plain"
STRALIGN = "left"
NUMALIGN = "left"
FLOATFMT = ".1f"

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

    headers = ["Name", "Sell volume", "Buy volume", "Volume diff", "Buy price", "Sell price",
               "Price diff"]
    table = tabulate(_get_highdemanded()[:count], headers=headers,
                     tablefmt=TABLEFMT,
                     stralign=STRALIGN,
                     numalign=NUMALIGN,
                     floatfmt=FLOATFMT)
    date_string = datetime.utcfromtimestamp(items.timestamps[-1] / 1000).strftime("%Y-%m-%d %H:%M:%S")
    await ctx.send(f'Current ({date_string}) high-demanded items:\n`' + table + '`')


@bot.command()
async def graph(ctx, attribute: typing.Optional[str] = None, count: typing.Optional[int] = 5):
    if attribute is None and count == 5:
        help_msg = "Attributes you can use:\n"
        help_msg += "buyPrice - price to buy item\n" \
                    "buyVolume - sum of all buy order volumes\n" \
                    "buyMovingWeek - how much buy price changed since last week\n" \
                    "buyOrders - buy orders quantity\n" \
                    "sellPrice - price to sell item\n" \
                    "sellVolume - sum of all sell order volumes\n" \
                    "sellOrders - sell orders quantity\n"
        await ctx.send(help_msg)
        return

    try:
        count = int(count)
    except ValueError or TypeError:
        await ctx.send("Couldn't parse argument")
        return

    if count > 10 or count < 1:
        await ctx.send(f'Argument should be between 1 and 10')
        return

    try:
        graph_filename = _get_top_graph(attribute, count)
    except KeyError:
        await ctx.send("No such attribute!")
        return
    graph_file = discord.File(graph_filename, filename="graph.png")
    await ctx.send("Here's your graph", file=graph_file)


# depth-1 crafting income generator
@bot.command()
async def profitablecraft(ctx):
    # TODO: hardcoded for now
    LIMIT = 7
    last_batch = items.last_batch
    profits = {}
    for item in last_batch:
        if item.bazaarStatus["buyVolume"] == 0 and item.bazaarStatus["sellVolume"] == 0:
            continue
        try:
            ingredients = item.get_ingredients()
            ingredients_price = 0

            for i in ingredients.keys():
                ingredients_price += ingredients[i] * last_batch[i].bazaarStatus["buyPrice"]
            # TODO: maybe use median sell price
            if item.bazaarStatus["sellPrice"] > ingredients_price:
                profits[item.internalName] = (item.bazaarStatus["sellPrice"] - ingredients_price, ingredients)
        except items.ItemNotFoundError:
            # log.info(f"Not found:{item.product_id}")
            continue
        except items.NoRecipeError:
            # log.info(f"Recipe not found:{item.product_id}")
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
                                  tablefmt=TABLEFMT, stralign=STRALIGN, numalign=NUMALIGN, floatfmt=FLOATFMT) + '`')


def _get_highdemanded():
    volume_diffs = {}
    for item in items.last_batch:
        if item.bazaarStatus["buyVolume"] == 0 and item.bazaarStatus["sellVolume"] == 0:
            continue
        volume_diff = item.bazaarStatus["buyVolume"] - item.bazaarStatus["sellVolume"]
        volume_diffs[item] = volume_diff
    # Generate top list
    top_list = []
    while len(volume_diffs) > 0:
        max_diff = -999999999
        max_item = ""
        # Find max diff
        for key in volume_diffs.keys():
            if volume_diffs[key] > max_diff:
                max_item = key
                max_diff = volume_diffs[key]
        status = max_item.bazaarStatus
        top_list.append(
            [max_item.internalName, status["sellVolume"],
             status["buyVolume"], max_diff, status["buyPrice"],
             status["sellPrice"],
             status["buyPrice"] - status["sellPrice"]])
        volume_diffs.pop(max_item)
    return top_list


def _get_top_graph(attribute: str, count: int):
    stats_at_timestamp = {}
    batches = database.get_all_products_batches()
    for batch in batches:
        leaders = sorted(batch, key=lambda k: k.__getattribute__("bazaarStatus")[attribute], reverse=True)
        stats_at_timestamp[batch.timestamp] = leaders[:count]

    timestamps = list(stats_at_timestamp.keys())
    stat = {}
    for ts_num in range(len(timestamps)):
        leaders = stats_at_timestamp[timestamps[ts_num]]

        for item in leaders:
            if item.internalName not in stat.keys():
                stat[item.internalName] = []
                # Use None as value for all previous timestamps
                for _ in range(ts_num):
                    stat[item.internalName].append(None)
                stat[item.internalName].append(item.bazaarStatus[attribute])
            else:
                # An item can still be a leader, or it can "skip" a few ticks
                if ts_num == len(stat[item.internalName]):
                    stat[item.internalName].append(item.bazaarStatus[attribute])
                else:
                    # Use None as value for all skipped timestamps
                    for _ in range(ts_num - len(stat[item.internalName])):
                        stat[item.internalName].append(None)
                    stat[item.internalName].append(item.bazaarStatus[attribute])

    # Now we have list [timestamps] and [sell_volumes] for every leader at those stamps
    # Plotting
    px = 1 / plt.rcParams['figure.dpi']  # pixel in inches
    fig, ax = plt.subplots(figsize=(1000 * px, 1000 * px))
    for internal_name in stat.keys():
        ax.plot(list(datetime.utcfromtimestamp(i / 1000) for i in timestamps), stat[internal_name],
                label=internal_name)
    ax.set(xlabel='Timestamp', ylabel=attribute,
           title=f'{attribute} leaders by timestamp')
    ax.grid()
    ax.legend()

    fig.savefig("graphs/test.png")
    return "graphs/test.png"


def _update_bazaar_data():
    bazaar_data = requests.get(f'{url}/bazaar?key={HYPIXEL_API_KEY}').json()
    items.last_batch = database.add_products_batch(bazaar_data)
    items.timestamps.append(items.last_batch.timestamp)


# Setup and start the bot
@tasks.loop(minutes=1)
async def do_update():
    # Update SkyBlock's bazaar data
    _update_bazaar_data()

    # Update high demand products message
    message = await bot.get_channel(BOT_CHANNEL_ID).fetch_message(HIGHDEMAND_MESSAGE_ID)

    headers = ["Name", "Sell volume", "Buy volume", "Volume diff", "Buy price", "Sell price", "Price diff"]
    table = tabulate(_get_highdemanded()[:10],
                     headers=headers,
                     tablefmt=TABLEFMT,
                     stralign=STRALIGN,
                     numalign=NUMALIGN,
                     floatfmt=FLOATFMT)
    date_string = datetime.utcfromtimestamp(items.timestamps[-1] / 1000).strftime("%Y-%m-%d %H:%M:%S")

    log.info("Updating pinned highdemand message")
    await message.edit(content=f'Current high-demanded items (updated on {date_string}' + '\n`' + table + '`',
                       suppress=True)


@bot.event
async def on_ready():
    do_update.start()
    log.info('SSB Started')


bot.run(DISCORD_TOKEN)
