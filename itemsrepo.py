import json
import logging
# TODO: reformat to class

log = logging.getLogger(__name__)

# TODO: move to os.environ
ITEMS_REPO_PATH = "./NotEnoughUpdates-REPO/items"


def get_item(item_internal_name: str):
    item_file = ITEMS_REPO_PATH + '/' + item_internal_name
    try:
        return json.load(open(item_file))
    except FileNotFoundError:
        log.info(f"Couldn't find item repo file: {item_file}")
        raise ItemNotFoundError


def get_ingredients(item_internal_name: str):
    try:
        recipe = json.load(open(ITEMS_REPO_PATH + '/' + item_internal_name + '.json'))["recipe"]
        result = {}
        for i in recipe.values():
            if i != '':
                if i in result.keys():
                    result[i] += 1
                else:
                    result[i] = 1
        return result
    except FileNotFoundError:
        raise ItemNotFoundError
    except KeyError:
        raise NoRecipeError


class ItemNotFoundError(BaseException):
    pass


class NoRecipeError(BaseException):
    pass
