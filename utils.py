import discord
from tabulate import tabulate

# Set up tabulate
TABLEFMT = "plain"
STRALIGN = "left"
NUMALIGN = "left"
FLOATFMT = ".1f"


def get_table_page(data, headers, page, per_page=10):
    pages = len(data) / per_page
    if page > pages + 1:
        raise IndexError
    else:
        table = tabulate(data[per_page * (page - 1):per_page * page], headers=headers,
                         tablefmt=TABLEFMT, stralign=STRALIGN, numalign=NUMALIGN, floatfmt=FLOATFMT)

    if per_page * page + 1 <= len(data):
        pagination_embed = discord.Embed(
            title=f'Results {per_page * (page - 1) + 1}-{per_page * page}\n Total: {len(data)}')
    else:
        pagination_embed = discord.Embed(
            title=f'Results {per_page * (page - 1) + 1}-{len(data)}\n Total: {len(data)}')
    return table, pagination_embed
