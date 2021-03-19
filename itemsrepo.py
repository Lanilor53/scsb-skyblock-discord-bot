import json

# TODO: reformat to class

# TODO: move to os.environ
ITEMS_REPO_PATH = "./NotEnoughUpdates-REPO/items"


def get_item(item_internal_name: str):
    try:
        return json.load(open(ITEMS_REPO_PATH + '/' + item_internal_name))
    except FileNotFoundError:
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
