import source as src
import xbmcgui
from strings import *

database = src.Database()
database.clearDatabase()
database.close()

xbmcgui.Dialog().ok(strings(CLEAR_CACHE), strings(DONE))
