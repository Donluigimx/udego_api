import imghdr
import uuid
from base64 import b64decode

import requests
from xml.etree.ElementTree import fromstring

from django.core.files.base import ContentFile


def udeg_valida(code=None, nip=None, *args, **kwargs):
    if code is None or nip is None:
        raise Exception('Code and nip are mandatory fields')
    headers = {'content-type': 'text/xml'}
    body = """<?xml version="1.0" encoding="UTF-8"?>
    <SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:SOAP-ENC="http://schemas.xmlsoap.org/soap/encoding/" xmlns:ns1="http://webservice/IWebServiceLogon.xsd" xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/" xmlns:tns="http://webservice/Logon.wsdl" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
       <SOAP-ENV:Body>
          <mns:valida xmlns:mns="WebServiceLogon" SOAP-ENV:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
             <usuario xsi:type="xsd:string">{0}</usuario>
             <password xsi:type="xsd:string">{1}</password>
             <key xsi:type="xsd:string">UdGSIIAUWebServiceValidaUsuario</key>
          </mns:valida>
       </SOAP-ENV:Body>
    </SOAP-ENV:Envelope>
    """.format(code, nip)

    r = requests.post(
        url='http://iasv2.siiau.udg.mx/WebServiceLogon/WebServiceLogon?wsdl',
        data=body,
        headers=headers,
    )

    return fromstring(r.text)[0][0][0].text


def from_b64(b64_data=''):
    """

    :param b64_data:
    :return:
    """
    if 'data:' in b64_data and ';base64,' in b64_data:
        # Break out the header from the base64 content
        header, b64_data = b64_data.split(';base64,')
    try:
        data = b64decode(b64_data)
    except TypeError:
        raise Exception('Base64Image cannot be decoded')
    name = str(uuid.uuid4())[:12]
    extension = imghdr.what(name, data)
    print(extension)
    extension = "jpg" if extension == "jpeg" else extension
    return ContentFile(data), "{0}.{1}".format(name, extension)
