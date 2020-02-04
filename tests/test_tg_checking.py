from seshat.models.tg_checking import error_log
from seshat.models.textgrids import SingleAnnotatorTextGrid
from textgrid import TextGrid, IntervalTier
from mongoengine import connect


connect('mongoenginetest', host='mongomock://localhost')

def test_tier_duplication():
    error_log.flush()
    tg = TextGrid()
    interval = IntervalTier("A", minTime=0, maxTime=10)
    tg.tiers = [interval]
    tg_doc = SingleAnnotatorTextGrid.from_textgrid(tg, [], None)
    tg_doc.check()


def test_missing_tier():
    pass