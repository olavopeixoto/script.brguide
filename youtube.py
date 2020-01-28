import urllib2
import re
import json


def geturl(url):

    try:
        request = urllib2.Request(url)
        response = urllib2.urlopen(request)
        webpage = response.read()

        mobj = re.search(r';ytplayer.config = ({.*?});', webpage)
        player_config = json.loads(mobj.group(1))

        player_response_string = player_config['args']['player_response']

        player_response = json.loads(player_response_string)

        return player_response['streamingData']['hlsManifestUrl']

    except:
        return ''
