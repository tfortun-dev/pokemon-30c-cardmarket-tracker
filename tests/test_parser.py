import importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location("tracker",Path(__file__).parents[1]/"scraper"/"main.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def test_price():
    assert m.price("299,00 €")==299.0
    assert m.price("2 399,00 €")==2399.0
def test_condition():
    assert m.condition("Near Mint")=="NM"
def test_rarity():
    assert m.rarity("30C 157")=="Futuriste rare"
