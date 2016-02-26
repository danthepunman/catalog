import base64
import hashlib
import hmac
import time
from urllib import quote

from default_config import AWSACCESSKEYID, AWSSECRETKEY


# Base class for working with the Amazon API
class AmazonApi(object):
    base_url = 'webservices.amazon.com'
    service = 'AWSECommerceService'
    aws_access_key_id = AWSACCESSKEYID
    associate_tag = 'danthepunman-20'
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
    parameters = dict(search_index=None, keywords=None, IdType=None, ItemId=None, Operation=None)
    response = dict(group=None, browsenode=None, page=None, sort=None)
    search_index = None

    # Creates the url for an Amazon API request
    @classmethod
    def url_creation(cls):
        # All the parameters that might be used
        url_params = dict(
            Service=cls.service,
            AWSAccessKeyId=cls.aws_access_key_id,
            AssociateTag=cls.associate_tag,
            Operation=cls.parameters['Operation'],
            SearchIndex=cls.parameters['search_index'],
            Keywords=cls.parameters['keywords'],
            IdType=cls.parameters['IdType'],
            ItemId=cls.parameters['ItemId'],
            ResponseGroup=cls.response['group'],
            Sort=cls.response['sort'],
            BrowseNode=cls.response['browsenode'],
            ItemPage=cls.response['page'],
            Timestamp=cls.timestamp
        )
        # Sort the parameters
        sorted_param = url_params.items()
        sorted_param.sort()
        # Join the parameters keys with their values
        params_to_encode = '&'.join(['%s=%s' % (k,quote(str(v))) for (k,v) in sorted_param if v])
        # Sets the string that needs to be signed
        string_for_signing = "GET"+"\n"+cls.base_url+"\n"+"/onca/xml"+"\n"+params_to_encode.encode('utf-8')
        # Creates the signature
        signature = quote(base64.b64encode(hmac.new(AWSSECRETKEY, string_for_signing, hashlib.sha256).digest()))
        # Compiles the request with the signature to make the url
        url_result = 'http://'+cls.base_url+'/onca/xml?'+params_to_encode.encode('utf-8')+'&Signature='+signature
        return url_result


# The class if searching for a Amazon Node
class AmazonNodeSearch(AmazonApi):
    def __init__(self, item_id):
        self.item_id = item_id
        self.parameters['IdType'] = 'ASIN'
        self.parameters['ItemId'] = item_id
        self.parameters['Operation'] = 'ItemLookup'
        self.response['group'] = "BrowseNodes"
        # The following are reset to None so they will be left out of the request
        self.parameters['search_index'] = None
        self.parameters['keywords'] = None
        self.response['browsenode'] = None
        self.parameters['sort'] = None
        self.response['page'] = None


# The class to get items
class AmazonItemsSearch(AmazonApi):
    def __init__(self, browse_node, search_index, keywords, page):
        self.browse_node = browse_node
        self.search_index = search_index
        self.keywords = keywords
        self.response['page'] = page
        self.parameters['search_index'] = search_index
        self.parameters['Operation'] = 'ItemSearch'
        self.parameters['keywords'] = keywords
        self.response['browsenode'] = browse_node
        self.response['group'] = 'Images,ItemAttributes'
        self.parameters['IdType'] = None
        self.parameters['ItemId'] = None
        self.parameters['sort'] = 'salesrank'


# The class to use with thumbtacks when the users wants to suggest an item
class AmazonASINCheck(AmazonApi):
    def __init__(self, asin):
        self.parameters['ItemId'] = asin
        self.parameters['IdType'] = 'ASIN'
        self.parameters['Operation'] = 'ItemLookup'
        self.response['group'] = 'Images,ItemAttributes'
        self.parameters['search_index'] = None
        self.parameters['keywords'] = None
        self.response['sort'] = None
        self.response['browsenode'] = None
        self.response['page'] = None
