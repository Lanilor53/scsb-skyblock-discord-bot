import json
import logging

log = logging.getLogger(__name__)

last_batch = None
timestamps = []

ITEMS_REPO_PATH = "./NotEnoughUpdates-REPO/items"


class Item:
    internalName = None
    displayName = None
    bazaarStatus = None
    recipe = None

    def __init__(self, bazaar_item):
        self.bazaarStatus = {"buyPrice": bazaar_item.buy_price, "buyVolume": bazaar_item.buy_volume,
                             "buyMovingWeek": bazaar_item.buy_moving_week, "buyOrders": bazaar_item.buy_orders,
                             "sellPrice": bazaar_item.sell_price, "sellVolume": bazaar_item.sell_volume,
                             "sellOrders": bazaar_item.sell_orders}
        self.internalName = bazaar_item.product_id

        item_file = ITEMS_REPO_PATH + '/' + self.internalName + '.json'
        try:
            item_json = json.load(open(item_file))
            self.displayName = item_json["displayname"]
            while self.displayName[1] == "§":
                self.displayName = self.displayName[3:]
            try:
                self.recipe = item_json["recipe"]
            except KeyError:
                pass
        except FileNotFoundError:
            log.info(f"Couldn't find item repo file: {item_file}")
            raise ItemNotFoundError

    def get_ingredients(self):
        if self.recipe is None:
            raise NoRecipeError
        result = {}

        for i in self.recipe.values():
            if i != '':
                splitted = i.split(":")
                name = splitted[0]
                item = last_batch[name]
                if len(splitted) > 1:
                    count = int(splitted[1])
                else:
                    count = 1
                if item in result.keys():
                    result[item] += count
                else:
                    result[item] = count
        return result


class ItemBatch:
    _items = None
    timestamp = None

    def __init__(self, items: list, timestamp: int):
        self._items = items
        self.timestamp = timestamp

    def __iter__(self):
        return iter(self._items)

    def __getitem__(self, item):
        for i in self._items:
            if i.internalName == item:
                return i
        raise KeyError

    def __len__(self):
        return len(self._items)

    def __str__(self):
        return str(self._items)


class ItemNotFoundError(BaseException):
    pass


class NoRecipeError(BaseException):
    pass
