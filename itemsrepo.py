import json

# TODO: move to os.environ
ITEMS_REPO_PATH = "./NotEnoughUpdates-REPO/items"


def get_item(item_internal_name: str):
    return json.load(open(ITEMS_REPO_PATH+'/'+item_internal_name))
