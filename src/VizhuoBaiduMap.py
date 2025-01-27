# -*- coding: utf-8 -*- 
import requests
import os
import re
import csv
import json
import time

import wx
import wx.xrc

import frame
import threading

from pubsub import pub
from bs4 import BeautifulSoup

class BaiduMap():
	"""docstring for BaiduMap"""
	def __init__(self):
		super(BaiduMap, self).__init__()

	def getCityData(self,cityName):

		try:
			webData = requests.get("http://map.baidu.com/?newmaOriginQueryp=1&qt=cur&ie=utf-8&wd=" + cityName + "&oue=1&res=jc").text
			jsonData = json.loads(webData)

			if 'weather' in jsonData: #存在天气预报的情况下
				weatherData = json.loads(jsonData['weather'])
				wx.CallAfter(pub.sendMessage, "updateText", content=weatherData['_update_time']+" PM2.5:"+weatherData['pm25']+weatherData['weather0']+"["+weatherData['temp0']+"]["+weatherData['wind0']+"]")
			if 'cur_area_id' in jsonData:
				wx.CallAfter(pub.sendMessage, "updateText", content="城市id:" + str(jsonData['cur_area_id'])+",小兵已待命!")
				return jsonData['cur_area_id']
			else:
				return -1

		except Exception as e:
			raise

	def createAndWrite(self,fileName,rowHeader,rowData=[]):

		if os.path.exists(fileName):
			fileName = str(time.time()) + "_" + fileName
		wx.CallAfter(pub.sendMessage, "updateText", content="writing:" + fileName)
		csvFile = open(fileName,'w',newline='')
		writer  = csv.writer(csvFile)

		writer.writerow(rowHeader)
		if len(rowData) > 0:
			writer.writerows(rowData)
		csvFile.close()

	def checkArr(self,checkArr,argv):
		pass

	def getMapData(self,cityName,cityId,info_):

		if cityId < 0 :
			return -1

		loopValue = 1
		loopCount = 1

		allData   = []

		qt        = "s"
		rn        = "10"
		modNum    = "10"

		while loopValue <= loopCount:

			getUrl    = "http://api.map.baidu.com/?qt=" + qt + "&c=" + str(cityId) + "&wd=" + info_ + "&rn=" + rn + "&pn=" + str(loopValue - 1) + "&ie=utf-8&oue=1&fromproduct=jsapi&res=api&callback=BMap._rd._cbk7303&ak=E4805d16520de693a3fe707cdc962045";

			webData   = requests.get(getUrl).text
			tempValue = int(re.search("\"total\":([\\s\\S]*?),",webData).group(1)) #数量

			print(getUrl)
			if tempValue > 0:
				if loopValue == 1:
					modNum    = tempValue % 10 # 第一次
					if modNum > 0:
						loopCount = (int)(tempValue / 10 + 1)
					else :
						loopCount = (int)(tempValue / 10)

				reJson   = re.search("content\":([\\s\\S]*?),\"current_city",webData).group(1)
				jsonData = json.loads(reJson)
				# 数据处理
				wx.CallAfter(pub.sendMessage, "updateText", content="retrieving: page " + str(loopValue))
				# print(jsonData)
				for x in range(0,len(jsonData)):
					try:
						print(jsonData[x])
						tempArr = [str(jsonData[x]['name']),str(jsonData[x]['addr'])] # 名称 地址

						tempArr.append(str(jsonData[x].get('ext').get('detail_info').get('overall_rating')))

						tempArr.append(str(jsonData[x].get('ext').get('detail_info').get('price')))

						tempArr.append(str(jsonData[x].get('ext').get('detail_info').get('shop_hours')))

						tempArr.append(str(jsonData[x].get('ext').get('detail_info').get('phone')).replace(","," 或 ")) 


						tempArr.append(str(jsonData[x].get('ext').get('detail_info').get('point').get('x')))
						tempArr.append(str(jsonData[x].get('ext').get('detail_info').get('point').get('y')))

						cater_tag = str(jsonData[x].get('ext').get('detail_info').get('short_comm'))

						if cater_tag == "None":
							cater_tag = str(jsonData[x].get('ext').get('detail_info').get('cater_tag'))

						tempArr.append(cater_tag) 

						tempArr.append(str(jsonData[x].get('address_norm'))) # 详细地址

						allData.append(tempArr)

					except KeyError as e:
						print('aa:' + str(e))

					except Exception as exception:
						print(str(exception))
						# print(jsonData[x])
						# exit()
					
				# 处理结束
				loopValue = loopValue + 1
			else :
				break

		if len(allData) > 0:
			rowHeader = ['name','address','overall_rating','price','shop_hours','phone','point_x','point_y','short_comm','address_norm']

			wx.CallAfter(pub.sendMessage, "updateText", content="ok . writing file!!!")

			self.createAndWrite(str(cityName) + "_" + re.sub(r"[\/\\\:\*\?\"\<\>\|\$$]","_",info_) + ".csv",rowHeader,allData)

			wx.CallAfter(pub.sendMessage, "updateText", content="over")
		else :
			wx.CallAfter(pub.sendMessage, "updateText", content="error content")

class windowGUI(frame.MyFrame1):
	"""docstring for windowGUI"""
	obj = BaiduMap()
	starting = False
	def __init__(self,parent):
		super(windowGUI, self).__init__(parent)
		pub.subscribe(self.setStBool, "setStBool")

	def __del__(self):
		pass

	def checkCity( self, event ):
		if int(self.obj.getCityData(self.m_comboBox2.GetValue())) > 0:
			wx.MessageDialog(None, u"信息正确!", u"城市验证",wx.ICON_QUESTION).ShowModal()
		else :
			wx.MessageDialog(None, u"验证失败!", u"城市验证",wx.ICON_QUESTION).ShowModal()

	def startJob( self, event ):

		if not self.starting:

			cityText     = self.m_comboBox2.GetValue() # 城市
			locationText = self.m_textCtrl4.GetValue() # 地点
			articleText  = self.m_textCtrl5.GetValue() # 物品

			if cityText.strip():
				if articleText.strip():
					if  locationText.strip():
						articleText = locationText + "$$" + articleText
					self.starting = True
					newThread = webThread(1,"Thread-1",1,cityText,articleText)
					newThread.start()
				else :
					wx.MessageDialog(None, u"检索物不能为空", u"Tip:",wx.ICON_QUESTION).ShowModal()
			else :
				wx.MessageDialog(None, u"城市不能为空", u"Tip:",wx.ICON_QUESTION).ShowModal()
		else : 
			wx.MessageDialog(None, u"线程运行中", u"Tip:",wx.ICON_QUESTION).ShowModal()

	def setStBool(self, msg) :
		self.starting = msg

class webThread(threading.Thread):
	"""docstring for webThread"""
	def __init__(self,threadID, name,counter,cityText,cityCode,articleText):

		super(webThread, self).__init__()
		threading.Thread.__init__(self)
		self.threadID    = threadID
		self.name        = name
		self.counter     = counter
		self.cityText    = cityText
		self.cityCode = cityCode
		self.articleText = articleText

	def run(self):
		obj = BaiduMap()
		obj.getMapData(self.cityText,obj.getCityData(self.cityText),self.articleText)

	def __del__(self):
		wx.CallAfter(pub.sendMessage, "setStBool", msg=False)

if __name__ == '__main__':

	app = wx.App(False)

	params=[
    {
        "id": 1,
        "city_name": "北京市",
        "city_adcode": 110100,
        "province_adcode": 110000,
        "province_id": 1
    },
    {
        "id": 2,
        "city_name": "天津市",
        "city_adcode": 120100,
        "province_adcode": 120000,
        "province_id": 2
    },
    {
        "id": 3,
        "city_name": "石家庄市",
        "city_adcode": 130100,
        "province_adcode": 130000,
        "province_id": 3
    },
    {
        "id": 4,
        "city_name": "唐山市",
        "city_adcode": 130200,
        "province_adcode": 130000,
        "province_id": 3
    },
    {
        "id": 5,
        "city_name": "秦皇岛市",
        "city_adcode": 130300,
        "province_adcode": 130000,
        "province_id": 3
    },
    {
        "id": 6,
        "city_name": "邯郸市",
        "city_adcode": 130400,
        "province_adcode": 130000,
        "province_id": 3
    },
    {
        "id": 7,
        "city_name": "邢台市",
        "city_adcode": 130500,
        "province_adcode": 130000,
        "province_id": 3
    },
    {
        "id": 8,
        "city_name": "保定市",
        "city_adcode": 130600,
        "province_adcode": 130000,
        "province_id": 3
    },
    {
        "id": 9,
        "city_name": "张家口市",
        "city_adcode": 130700,
        "province_adcode": 130000,
        "province_id": 3
    },
    {
        "id": 10,
        "city_name": "承德市",
        "city_adcode": 130800,
        "province_adcode": 130000,
        "province_id": 3
    },
    {
        "id": 11,
        "city_name": "沧州市",
        "city_adcode": 130900,
        "province_adcode": 130000,
        "province_id": 3
    },
    {
        "id": 12,
        "city_name": "廊坊市",
        "city_adcode": 131000,
        "province_adcode": 130000,
        "province_id": 3
    },
    {
        "id": 13,
        "city_name": "衡水市",
        "city_adcode": 131100,
        "province_adcode": 130000,
        "province_id": 3
    },
    {
        "id": 14,
        "city_name": "太原市",
        "city_adcode": 140100,
        "province_adcode": 140000,
        "province_id": 4
    },
    {
        "id": 15,
        "city_name": "大同市",
        "city_adcode": 140200,
        "province_adcode": 140000,
        "province_id": 4
    },
    {
        "id": 16,
        "city_name": "阳泉市",
        "city_adcode": 140300,
        "province_adcode": 140000,
        "province_id": 4
    },
    {
        "id": 17,
        "city_name": "长治市",
        "city_adcode": 140400,
        "province_adcode": 140000,
        "province_id": 4
    },
    {
        "id": 18,
        "city_name": "晋城市",
        "city_adcode": 140500,
        "province_adcode": 140000,
        "province_id": 4
    },
    {
        "id": 19,
        "city_name": "朔州市",
        "city_adcode": 140600,
        "province_adcode": 140000,
        "province_id": 4
    },
    {
        "id": 20,
        "city_name": "晋中市",
        "city_adcode": 140700,
        "province_adcode": 140000,
        "province_id": 4
    },
    {
        "id": 21,
        "city_name": "运城市",
        "city_adcode": 140800,
        "province_adcode": 140000,
        "province_id": 4
    },
    {
        "id": 22,
        "city_name": "忻州市",
        "city_adcode": 140900,
        "province_adcode": 140000,
        "province_id": 4
    },
    {
        "id": 23,
        "city_name": "临汾市",
        "city_adcode": 141000,
        "province_adcode": 140000,
        "province_id": 4
    },
    {
        "id": 24,
        "city_name": "吕梁市",
        "city_adcode": 141100,
        "province_adcode": 140000,
        "province_id": 4
    },
    {
        "id": 25,
        "city_name": "呼和浩特市",
        "city_adcode": 150100,
        "province_adcode": 150000,
        "province_id": 5
    },
    {
        "id": 26,
        "city_name": "包头市",
        "city_adcode": 150200,
        "province_adcode": 150000,
        "province_id": 5
    },
    {
        "id": 27,
        "city_name": "乌海市",
        "city_adcode": 150300,
        "province_adcode": 150000,
        "province_id": 5
    },
    {
        "id": 28,
        "city_name": "赤峰市",
        "city_adcode": 150400,
        "province_adcode": 150000,
        "province_id": 5
    },
    {
        "id": 29,
        "city_name": "通辽市",
        "city_adcode": 150500,
        "province_adcode": 150000,
        "province_id": 5
    },
    {
        "id": 30,
        "city_name": "鄂尔多斯市",
        "city_adcode": 150600,
        "province_adcode": 150000,
        "province_id": 5
    },
    {
        "id": 31,
        "city_name": "呼伦贝尔市",
        "city_adcode": 150700,
        "province_adcode": 150000,
        "province_id": 5
    },
    {
        "id": 32,
        "city_name": "巴彦淖尔市",
        "city_adcode": 150800,
        "province_adcode": 150000,
        "province_id": 5
    },
    {
        "id": 33,
        "city_name": "乌兰察布市",
        "city_adcode": 150900,
        "province_adcode": 150000,
        "province_id": 5
    },
    {
        "id": 34,
        "city_name": "兴安盟",
        "city_adcode": 152200,
        "province_adcode": 150000,
        "province_id": 5
    },
    {
        "id": 35,
        "city_name": "锡林郭勒盟",
        "city_adcode": 152500,
        "province_adcode": 150000,
        "province_id": 5
    },
    {
        "id": 36,
        "city_name": "阿拉善盟",
        "city_adcode": 152900,
        "province_adcode": 150000,
        "province_id": 5
    },
    {
        "id": 37,
        "city_name": "沈阳市",
        "city_adcode": 210100,
        "province_adcode": 210000,
        "province_id": 6
    },
    {
        "id": 38,
        "city_name": "大连市",
        "city_adcode": 210200,
        "province_adcode": 210000,
        "province_id": 6
    },
    {
        "id": 39,
        "city_name": "鞍山市",
        "city_adcode": 210300,
        "province_adcode": 210000,
        "province_id": 6
    },
    {
        "id": 40,
        "city_name": "抚顺市",
        "city_adcode": 210400,
        "province_adcode": 210000,
        "province_id": 6
    },
    {
        "id": 41,
        "city_name": "本溪市",
        "city_adcode": 210500,
        "province_adcode": 210000,
        "province_id": 6
    },
    {
        "id": 42,
        "city_name": "丹东市",
        "city_adcode": 210600,
        "province_adcode": 210000,
        "province_id": 6
    },
    {
        "id": 43,
        "city_name": "锦州市",
        "city_adcode": 210700,
        "province_adcode": 210000,
        "province_id": 6
    },
    {
        "id": 44,
        "city_name": "营口市",
        "city_adcode": 210800,
        "province_adcode": 210000,
        "province_id": 6
    },
    {
        "id": 45,
        "city_name": "阜新市",
        "city_adcode": 210900,
        "province_adcode": 210000,
        "province_id": 6
    },
    {
        "id": 46,
        "city_name": "辽阳市",
        "city_adcode": 211000,
        "province_adcode": 210000,
        "province_id": 6
    },
    {
        "id": 47,
        "city_name": "盘锦市",
        "city_adcode": 211100,
        "province_adcode": 210000,
        "province_id": 6
    },
    {
        "id": 48,
        "city_name": "铁岭市",
        "city_adcode": 211200,
        "province_adcode": 210000,
        "province_id": 6
    },
    {
        "id": 49,
        "city_name": "朝阳市",
        "city_adcode": 211300,
        "province_adcode": 210000,
        "province_id": 6
    },
    {
        "id": 50,
        "city_name": "葫芦岛市",
        "city_adcode": 211400,
        "province_adcode": 210000,
        "province_id": 6
    },
    {
        "id": 51,
        "city_name": "长春市",
        "city_adcode": 220100,
        "province_adcode": 220000,
        "province_id": 7
    },
    {
        "id": 52,
        "city_name": "吉林市",
        "city_adcode": 220200,
        "province_adcode": 220000,
        "province_id": 7
    },
    {
        "id": 53,
        "city_name": "四平市",
        "city_adcode": 220300,
        "province_adcode": 220000,
        "province_id": 7
    },
    {
        "id": 54,
        "city_name": "辽源市",
        "city_adcode": 220400,
        "province_adcode": 220000,
        "province_id": 7
    },
    {
        "id": 55,
        "city_name": "通化市",
        "city_adcode": 220500,
        "province_adcode": 220000,
        "province_id": 7
    },
    {
        "id": 56,
        "city_name": "白山市",
        "city_adcode": 220600,
        "province_adcode": 220000,
        "province_id": 7
    },
    {
        "id": 57,
        "city_name": "松原市",
        "city_adcode": 220700,
        "province_adcode": 220000,
        "province_id": 7
    },
    {
        "id": 58,
        "city_name": "白城市",
        "city_adcode": 220800,
        "province_adcode": 220000,
        "province_id": 7
    },
    {
        "id": 59,
        "city_name": "延边朝鲜族自治州",
        "city_adcode": 222400,
        "province_adcode": 220000,
        "province_id": 7
    },
    {
        "id": 60,
        "city_name": "哈尔滨市",
        "city_adcode": 230100,
        "province_adcode": 230000,
        "province_id": 8
    },
    {
        "id": 61,
        "city_name": "齐齐哈尔市",
        "city_adcode": 230200,
        "province_adcode": 230000,
        "province_id": 8
    },
    {
        "id": 62,
        "city_name": "鸡西市",
        "city_adcode": 230300,
        "province_adcode": 230000,
        "province_id": 8
    },
    {
        "id": 63,
        "city_name": "鹤岗市",
        "city_adcode": 230400,
        "province_adcode": 230000,
        "province_id": 8
    },
    {
        "id": 64,
        "city_name": "双鸭山市",
        "city_adcode": 230500,
        "province_adcode": 230000,
        "province_id": 8
    },
    {
        "id": 65,
        "city_name": "大庆市",
        "city_adcode": 230600,
        "province_adcode": 230000,
        "province_id": 8
    },
    {
        "id": 66,
        "city_name": "伊春市",
        "city_adcode": 230700,
        "province_adcode": 230000,
        "province_id": 8
    },
    {
        "id": 67,
        "city_name": "佳木斯市",
        "city_adcode": 230800,
        "province_adcode": 230000,
        "province_id": 8
    },
    {
        "id": 68,
        "city_name": "七台河市",
        "city_adcode": 230900,
        "province_adcode": 230000,
        "province_id": 8
    },
    {
        "id": 69,
        "city_name": "牡丹江市",
        "city_adcode": 231000,
        "province_adcode": 230000,
        "province_id": 8
    },
    {
        "id": 70,
        "city_name": "黑河市",
        "city_adcode": 231100,
        "province_adcode": 230000,
        "province_id": 8
    },
    {
        "id": 71,
        "city_name": "绥化市",
        "city_adcode": 231200,
        "province_adcode": 230000,
        "province_id": 8
    },
    {
        "id": 72,
        "city_name": "大兴安岭地区",
        "city_adcode": 232700,
        "province_adcode": 230000,
        "province_id": 8
    },
    {
        "id": 73,
        "city_name": "上海市",
        "city_adcode": 310100,
        "province_adcode": 310000,
        "province_id": 9
    },
    {
        "id": 74,
        "city_name": "南京市",
        "city_adcode": 320100,
        "province_adcode": 320000,
        "province_id": 10
    },
    {
        "id": 75,
        "city_name": "无锡市",
        "city_adcode": 320200,
        "province_adcode": 320000,
        "province_id": 10
    },
    {
        "id": 76,
        "city_name": "徐州市",
        "city_adcode": 320300,
        "province_adcode": 320000,
        "province_id": 10
    },
    {
        "id": 77,
        "city_name": "常州市",
        "city_adcode": 320400,
        "province_adcode": 320000,
        "province_id": 10
    },
    {
        "id": 78,
        "city_name": "苏州市",
        "city_adcode": 320500,
        "province_adcode": 320000,
        "province_id": 10
    },
    {
        "id": 79,
        "city_name": "南通市",
        "city_adcode": 320600,
        "province_adcode": 320000,
        "province_id": 10
    },
    {
        "id": 80,
        "city_name": "连云港市",
        "city_adcode": 320700,
        "province_adcode": 320000,
        "province_id": 10
    },
    {
        "id": 81,
        "city_name": "淮安市",
        "city_adcode": 320800,
        "province_adcode": 320000,
        "province_id": 10
    },
    {
        "id": 82,
        "city_name": "盐城市",
        "city_adcode": 320900,
        "province_adcode": 320000,
        "province_id": 10
    },
    {
        "id": 83,
        "city_name": "扬州市",
        "city_adcode": 321000,
        "province_adcode": 320000,
        "province_id": 10
    },
    {
        "id": 84,
        "city_name": "镇江市",
        "city_adcode": 321100,
        "province_adcode": 320000,
        "province_id": 10
    },
    {
        "id": 85,
        "city_name": "泰州市",
        "city_adcode": 321200,
        "province_adcode": 320000,
        "province_id": 10
    },
    {
        "id": 86,
        "city_name": "宿迁市",
        "city_adcode": 321300,
        "province_adcode": 320000,
        "province_id": 10
    },
    {
        "id": 87,
        "city_name": "杭州市",
        "city_adcode": 330100,
        "province_adcode": 330000,
        "province_id": 11
    },
    {
        "id": 88,
        "city_name": "宁波市",
        "city_adcode": 330200,
        "province_adcode": 330000,
        "province_id": 11
    },
    {
        "id": 89,
        "city_name": "温州市",
        "city_adcode": 330300,
        "province_adcode": 330000,
        "province_id": 11
    },
    {
        "id": 90,
        "city_name": "嘉兴市",
        "city_adcode": 330400,
        "province_adcode": 330000,
        "province_id": 11
    },
    {
        "id": 91,
        "city_name": "湖州市",
        "city_adcode": 330500,
        "province_adcode": 330000,
        "province_id": 11
    },
    {
        "id": 92,
        "city_name": "绍兴市",
        "city_adcode": 330600,
        "province_adcode": 330000,
        "province_id": 11
    },
    {
        "id": 93,
        "city_name": "金华市",
        "city_adcode": 330700,
        "province_adcode": 330000,
        "province_id": 11
    },
    {
        "id": 94,
        "city_name": "衢州市",
        "city_adcode": 330800,
        "province_adcode": 330000,
        "province_id": 11
    },
    {
        "id": 95,
        "city_name": "舟山市",
        "city_adcode": 330900,
        "province_adcode": 330000,
        "province_id": 11
    },
    {
        "id": 96,
        "city_name": "台州市",
        "city_adcode": 331000,
        "province_adcode": 330000,
        "province_id": 11
    },
    {
        "id": 97,
        "city_name": "丽水市",
        "city_adcode": 331100,
        "province_adcode": 330000,
        "province_id": 11
    },
    {
        "id": 98,
        "city_name": "合肥市",
        "city_adcode": 340100,
        "province_adcode": 340000,
        "province_id": 12
    },
    {
        "id": 99,
        "city_name": "芜湖市",
        "city_adcode": 340200,
        "province_adcode": 340000,
        "province_id": 12
    },
    {
        "id": 100,
        "city_name": "蚌埠市",
        "city_adcode": 340300,
        "province_adcode": 340000,
        "province_id": 12
    },
    {
        "id": 101,
        "city_name": "淮南市",
        "city_adcode": 340400,
        "province_adcode": 340000,
        "province_id": 12
    },
    {
        "id": 102,
        "city_name": "马鞍山市",
        "city_adcode": 340500,
        "province_adcode": 340000,
        "province_id": 12
    },
    {
        "id": 103,
        "city_name": "淮北市",
        "city_adcode": 340600,
        "province_adcode": 340000,
        "province_id": 12
    },
    {
        "id": 104,
        "city_name": "铜陵市",
        "city_adcode": 340700,
        "province_adcode": 340000,
        "province_id": 12
    },
    {
        "id": 105,
        "city_name": "安庆市",
        "city_adcode": 340800,
        "province_adcode": 340000,
        "province_id": 12
    },
    {
        "id": 106,
        "city_name": "黄山市",
        "city_adcode": 341000,
        "province_adcode": 340000,
        "province_id": 12
    },
    {
        "id": 107,
        "city_name": "滁州市",
        "city_adcode": 341100,
        "province_adcode": 340000,
        "province_id": 12
    },
    {
        "id": 108,
        "city_name": "阜阳市",
        "city_adcode": 341200,
        "province_adcode": 340000,
        "province_id": 12
    },
    {
        "id": 109,
        "city_name": "宿州市",
        "city_adcode": 341300,
        "province_adcode": 340000,
        "province_id": 12
    },
    {
        "id": 110,
        "city_name": "六安市",
        "city_adcode": 341500,
        "province_adcode": 340000,
        "province_id": 12
    },
    {
        "id": 111,
        "city_name": "亳州市",
        "city_adcode": 341600,
        "province_adcode": 340000,
        "province_id": 12
    },
    {
        "id": 112,
        "city_name": "池州市",
        "city_adcode": 341700,
        "province_adcode": 340000,
        "province_id": 12
    },
    {
        "id": 113,
        "city_name": "宣城市",
        "city_adcode": 341800,
        "province_adcode": 340000,
        "province_id": 12
    },
    {
        "id": 114,
        "city_name": "福州市",
        "city_adcode": 350100,
        "province_adcode": 350000,
        "province_id": 13
    },
    {
        "id": 115,
        "city_name": "厦门市",
        "city_adcode": 350200,
        "province_adcode": 350000,
        "province_id": 13
    },
    {
        "id": 116,
        "city_name": "莆田市",
        "city_adcode": 350300,
        "province_adcode": 350000,
        "province_id": 13
    },
    {
        "id": 117,
        "city_name": "三明市",
        "city_adcode": 350400,
        "province_adcode": 350000,
        "province_id": 13
    },
    {
        "id": 118,
        "city_name": "泉州市",
        "city_adcode": 350500,
        "province_adcode": 350000,
        "province_id": 13
    },
    {
        "id": 119,
        "city_name": "漳州市",
        "city_adcode": 350600,
        "province_adcode": 350000,
        "province_id": 13
    },
    {
        "id": 120,
        "city_name": "南平市",
        "city_adcode": 350700,
        "province_adcode": 350000,
        "province_id": 13
    },
    {
        "id": 121,
        "city_name": "龙岩市",
        "city_adcode": 350800,
        "province_adcode": 350000,
        "province_id": 13
    },
    {
        "id": 122,
        "city_name": "宁德市",
        "city_adcode": 350900,
        "province_adcode": 350000,
        "province_id": 13
    },
    {
        "id": 123,
        "city_name": "南昌市",
        "city_adcode": 360100,
        "province_adcode": 360000,
        "province_id": 14
    },
    {
        "id": 124,
        "city_name": "景德镇市",
        "city_adcode": 360200,
        "province_adcode": 360000,
        "province_id": 14
    },
    {
        "id": 125,
        "city_name": "萍乡市",
        "city_adcode": 360300,
        "province_adcode": 360000,
        "province_id": 14
    },
    {
        "id": 126,
        "city_name": "九江市",
        "city_adcode": 360400,
        "province_adcode": 360000,
        "province_id": 14
    },
    {
        "id": 127,
        "city_name": "新余市",
        "city_adcode": 360500,
        "province_adcode": 360000,
        "province_id": 14
    },
    {
        "id": 128,
        "city_name": "鹰潭市",
        "city_adcode": 360600,
        "province_adcode": 360000,
        "province_id": 14
    },
    {
        "id": 129,
        "city_name": "赣州市",
        "city_adcode": 360700,
        "province_adcode": 360000,
        "province_id": 14
    },
    {
        "id": 130,
        "city_name": "吉安市",
        "city_adcode": 360800,
        "province_adcode": 360000,
        "province_id": 14
    },
    {
        "id": 131,
        "city_name": "宜春市",
        "city_adcode": 360900,
        "province_adcode": 360000,
        "province_id": 14
    },
    {
        "id": 132,
        "city_name": "抚州市",
        "city_adcode": 361000,
        "province_adcode": 360000,
        "province_id": 14
    },
    {
        "id": 133,
        "city_name": "上饶市",
        "city_adcode": 361100,
        "province_adcode": 360000,
        "province_id": 14
    },
    {
        "id": 134,
        "city_name": "济南市",
        "city_adcode": 370100,
        "province_adcode": 370000,
        "province_id": 15
    },
    {
        "id": 135,
        "city_name": "青岛市",
        "city_adcode": 370200,
        "province_adcode": 370000,
        "province_id": 15
    },
    {
        "id": 136,
        "city_name": "淄博市",
        "city_adcode": 370300,
        "province_adcode": 370000,
        "province_id": 15
    },
    {
        "id": 137,
        "city_name": "枣庄市",
        "city_adcode": 370400,
        "province_adcode": 370000,
        "province_id": 15
    },
    {
        "id": 138,
        "city_name": "东营市",
        "city_adcode": 370500,
        "province_adcode": 370000,
        "province_id": 15
    },
    {
        "id": 139,
        "city_name": "烟台市",
        "city_adcode": 370600,
        "province_adcode": 370000,
        "province_id": 15
    },
    {
        "id": 140,
        "city_name": "潍坊市",
        "city_adcode": 370700,
        "province_adcode": 370000,
        "province_id": 15
    },
    {
        "id": 141,
        "city_name": "济宁市",
        "city_adcode": 370800,
        "province_adcode": 370000,
        "province_id": 15
    },
    {
        "id": 142,
        "city_name": "泰安市",
        "city_adcode": 370900,
        "province_adcode": 370000,
        "province_id": 15
    },
    {
        "id": 143,
        "city_name": "威海市",
        "city_adcode": 371000,
        "province_adcode": 370000,
        "province_id": 15
    },
    {
        "id": 144,
        "city_name": "日照市",
        "city_adcode": 371100,
        "province_adcode": 370000,
        "province_id": 15
    },
    {
        "id": 145,
        "city_name": "临沂市",
        "city_adcode": 371300,
        "province_adcode": 370000,
        "province_id": 15
    },
    {
        "id": 146,
        "city_name": "德州市",
        "city_adcode": 371400,
        "province_adcode": 370000,
        "province_id": 15
    },
    {
        "id": 147,
        "city_name": "聊城市",
        "city_adcode": 371500,
        "province_adcode": 370000,
        "province_id": 15
    },
    {
        "id": 148,
        "city_name": "滨州市",
        "city_adcode": 371600,
        "province_adcode": 370000,
        "province_id": 15
    },
    {
        "id": 149,
        "city_name": "菏泽市",
        "city_adcode": 371700,
        "province_adcode": 370000,
        "province_id": 15
    },
    {
        "id": 150,
        "city_name": "郑州市",
        "city_adcode": 410100,
        "province_adcode": 410000,
        "province_id": 16
    },
    {
        "id": 151,
        "city_name": "开封市",
        "city_adcode": 410200,
        "province_adcode": 410000,
        "province_id": 16
    },
    {
        "id": 152,
        "city_name": "洛阳市",
        "city_adcode": 410300,
        "province_adcode": 410000,
        "province_id": 16
    },
    {
        "id": 153,
        "city_name": "平顶山市",
        "city_adcode": 410400,
        "province_adcode": 410000,
        "province_id": 16
    },
    {
        "id": 154,
        "city_name": "安阳市",
        "city_adcode": 410500,
        "province_adcode": 410000,
        "province_id": 16
    },
    {
        "id": 155,
        "city_name": "鹤壁市",
        "city_adcode": 410600,
        "province_adcode": 410000,
        "province_id": 16
    },
    {
        "id": 156,
        "city_name": "新乡市",
        "city_adcode": 410700,
        "province_adcode": 410000,
        "province_id": 16
    },
    {
        "id": 157,
        "city_name": "焦作市",
        "city_adcode": 410800,
        "province_adcode": 410000,
        "province_id": 16
    },
    {
        "id": 158,
        "city_name": "濮阳市",
        "city_adcode": 410900,
        "province_adcode": 410000,
        "province_id": 16
    },
    {
        "id": 159,
        "city_name": "许昌市",
        "city_adcode": 411000,
        "province_adcode": 410000,
        "province_id": 16
    },
    {
        "id": 160,
        "city_name": "漯河市",
        "city_adcode": 411100,
        "province_adcode": 410000,
        "province_id": 16
    },
    {
        "id": 161,
        "city_name": "三门峡市",
        "city_adcode": 411200,
        "province_adcode": 410000,
        "province_id": 16
    },
    {
        "id": 162,
        "city_name": "南阳市",
        "city_adcode": 411300,
        "province_adcode": 410000,
        "province_id": 16
    },
    {
        "id": 163,
        "city_name": "商丘市",
        "city_adcode": 411400,
        "province_adcode": 410000,
        "province_id": 16
    },
    {
        "id": 164,
        "city_name": "信阳市",
        "city_adcode": 411500,
        "province_adcode": 410000,
        "province_id": 16
    },
    {
        "id": 165,
        "city_name": "周口市",
        "city_adcode": 411600,
        "province_adcode": 410000,
        "province_id": 16
    },
    {
        "id": 166,
        "city_name": "驻马店市",
        "city_adcode": 411700,
        "province_adcode": 410000,
        "province_id": 16
    },
    {
        "id": 167,
        "city_name": "济源市",
        "city_adcode": 419001,
        "province_adcode": 410000,
        "province_id": 16
    },
    {
        "id": 168,
        "city_name": "武汉市",
        "city_adcode": 420100,
        "province_adcode": 420000,
        "province_id": 17
    },
    {
        "id": 169,
        "city_name": "黄石市",
        "city_adcode": 420200,
        "province_adcode": 420000,
        "province_id": 17
    },
    {
        "id": 170,
        "city_name": "十堰市",
        "city_adcode": 420300,
        "province_adcode": 420000,
        "province_id": 17
    },
    {
        "id": 171,
        "city_name": "宜昌市",
        "city_adcode": 420500,
        "province_adcode": 420000,
        "province_id": 17
    },
    {
        "id": 172,
        "city_name": "襄阳市",
        "city_adcode": 420600,
        "province_adcode": 420000,
        "province_id": 17
    },
    {
        "id": 173,
        "city_name": "鄂州市",
        "city_adcode": 420700,
        "province_adcode": 420000,
        "province_id": 17
    },
    {
        "id": 174,
        "city_name": "荆门市",
        "city_adcode": 420800,
        "province_adcode": 420000,
        "province_id": 17
    },
    {
        "id": 175,
        "city_name": "孝感市",
        "city_adcode": 420900,
        "province_adcode": 420000,
        "province_id": 17
    },
    {
        "id": 176,
        "city_name": "荆州市",
        "city_adcode": 421000,
        "province_adcode": 420000,
        "province_id": 17
    },
    {
        "id": 177,
        "city_name": "黄冈市",
        "city_adcode": 421100,
        "province_adcode": 420000,
        "province_id": 17
    },
    {
        "id": 178,
        "city_name": "咸宁市",
        "city_adcode": 421200,
        "province_adcode": 420000,
        "province_id": 17
    },
    {
        "id": 179,
        "city_name": "随州市",
        "city_adcode": 421300,
        "province_adcode": 420000,
        "province_id": 17
    },
    {
        "id": 180,
        "city_name": "恩施土家族苗族自治州",
        "city_adcode": 422800,
        "province_adcode": 420000,
        "province_id": 17
    },
    {
        "id": 181,
        "city_name": "仙桃市",
        "city_adcode": 429004,
        "province_adcode": 420000,
        "province_id": 17
    },
    {
        "id": 182,
        "city_name": "潜江市",
        "city_adcode": 429005,
        "province_adcode": 420000,
        "province_id": 17
    },
    {
        "id": 183,
        "city_name": "天门市",
        "city_adcode": 429006,
        "province_adcode": 420000,
        "province_id": 17
    },
    {
        "id": 184,
        "city_name": "神农架林区",
        "city_adcode": 429021,
        "province_adcode": 420000,
        "province_id": 17
    },
    {
        "id": 185,
        "city_name": "长沙市",
        "city_adcode": 430100,
        "province_adcode": 430000,
        "province_id": 18
    },
    {
        "id": 186,
        "city_name": "株洲市",
        "city_adcode": 430200,
        "province_adcode": 430000,
        "province_id": 18
    },
    {
        "id": 187,
        "city_name": "湘潭市",
        "city_adcode": 430300,
        "province_adcode": 430000,
        "province_id": 18
    },
    {
        "id": 188,
        "city_name": "衡阳市",
        "city_adcode": 430400,
        "province_adcode": 430000,
        "province_id": 18
    },
    {
        "id": 189,
        "city_name": "邵阳市",
        "city_adcode": 430500,
        "province_adcode": 430000,
        "province_id": 18
    },
    {
        "id": 190,
        "city_name": "岳阳市",
        "city_adcode": 430600,
        "province_adcode": 430000,
        "province_id": 18
    },
    {
        "id": 191,
        "city_name": "常德市",
        "city_adcode": 430700,
        "province_adcode": 430000,
        "province_id": 18
    },
    {
        "id": 192,
        "city_name": "张家界市",
        "city_adcode": 430800,
        "province_adcode": 430000,
        "province_id": 18
    },
    {
        "id": 193,
        "city_name": "益阳市",
        "city_adcode": 430900,
        "province_adcode": 430000,
        "province_id": 18
    },
    {
        "id": 194,
        "city_name": "郴州市",
        "city_adcode": 431000,
        "province_adcode": 430000,
        "province_id": 18
    },
    {
        "id": 195,
        "city_name": "永州市",
        "city_adcode": 431100,
        "province_adcode": 430000,
        "province_id": 18
    },
    {
        "id": 196,
        "city_name": "怀化市",
        "city_adcode": 431200,
        "province_adcode": 430000,
        "province_id": 18
    },
    {
        "id": 197,
        "city_name": "娄底市",
        "city_adcode": 431300,
        "province_adcode": 430000,
        "province_id": 18
    },
    {
        "id": 198,
        "city_name": "湘西土家族苗族自治州",
        "city_adcode": 433100,
        "province_adcode": 430000,
        "province_id": 18
    },
    {
        "id": 199,
        "city_name": "广州市",
        "city_adcode": 440100,
        "province_adcode": 440000,
        "province_id": 19
    },
    {
        "id": 200,
        "city_name": "韶关市",
        "city_adcode": 440200,
        "province_adcode": 440000,
        "province_id": 19
    },
    {
        "id": 201,
        "city_name": "深圳市",
        "city_adcode": 440300,
        "province_adcode": 440000,
        "province_id": 19
    },
    {
        "id": 202,
        "city_name": "珠海市",
        "city_adcode": 440400,
        "province_adcode": 440000,
        "province_id": 19
    },
    {
        "id": 203,
        "city_name": "汕头市",
        "city_adcode": 440500,
        "province_adcode": 440000,
        "province_id": 19
    },
    {
        "id": 204,
        "city_name": "佛山市",
        "city_adcode": 440600,
        "province_adcode": 440000,
        "province_id": 19
    },
    {
        "id": 205,
        "city_name": "江门市",
        "city_adcode": 440700,
        "province_adcode": 440000,
        "province_id": 19
    },
    {
        "id": 206,
        "city_name": "湛江市",
        "city_adcode": 440800,
        "province_adcode": 440000,
        "province_id": 19
    },
    {
        "id": 207,
        "city_name": "茂名市",
        "city_adcode": 440900,
        "province_adcode": 440000,
        "province_id": 19
    },
    {
        "id": 208,
        "city_name": "肇庆市",
        "city_adcode": 441200,
        "province_adcode": 440000,
        "province_id": 19
    },
    {
        "id": 209,
        "city_name": "惠州市",
        "city_adcode": 441300,
        "province_adcode": 440000,
        "province_id": 19
    },
    {
        "id": 210,
        "city_name": "梅州市",
        "city_adcode": 441400,
        "province_adcode": 440000,
        "province_id": 19
    },
    {
        "id": 211,
        "city_name": "汕尾市",
        "city_adcode": 441500,
        "province_adcode": 440000,
        "province_id": 19
    },
    {
        "id": 212,
        "city_name": "河源市",
        "city_adcode": 441600,
        "province_adcode": 440000,
        "province_id": 19
    },
    {
        "id": 213,
        "city_name": "阳江市",
        "city_adcode": 441700,
        "province_adcode": 440000,
        "province_id": 19
    },
    {
        "id": 214,
        "city_name": "清远市",
        "city_adcode": 441800,
        "province_adcode": 440000,
        "province_id": 19
    },
    {
        "id": 215,
        "city_name": "东莞市",
        "city_adcode": 441900,
        "province_adcode": 440000,
        "province_id": 19
    },
    {
        "id": 216,
        "city_name": "中山市",
        "city_adcode": 442000,
        "province_adcode": 440000,
        "province_id": 19
    },
    {
        "id": 217,
        "city_name": "潮州市",
        "city_adcode": 445100,
        "province_adcode": 440000,
        "province_id": 19
    },
    {
        "id": 218,
        "city_name": "揭阳市",
        "city_adcode": 445200,
        "province_adcode": 440000,
        "province_id": 19
    },
    {
        "id": 219,
        "city_name": "云浮市",
        "city_adcode": 445300,
        "province_adcode": 440000,
        "province_id": 19
    },
    {
        "id": 220,
        "city_name": "南宁市",
        "city_adcode": 450100,
        "province_adcode": 450000,
        "province_id": 20
    },
    {
        "id": 221,
        "city_name": "柳州市",
        "city_adcode": 450200,
        "province_adcode": 450000,
        "province_id": 20
    },
    {
        "id": 222,
        "city_name": "桂林市",
        "city_adcode": 450300,
        "province_adcode": 450000,
        "province_id": 20
    },
    {
        "id": 223,
        "city_name": "梧州市",
        "city_adcode": 450400,
        "province_adcode": 450000,
        "province_id": 20
    },
    {
        "id": 224,
        "city_name": "北海市",
        "city_adcode": 450500,
        "province_adcode": 450000,
        "province_id": 20
    },
    {
        "id": 225,
        "city_name": "防城港市",
        "city_adcode": 450600,
        "province_adcode": 450000,
        "province_id": 20
    },
    {
        "id": 226,
        "city_name": "钦州市",
        "city_adcode": 450700,
        "province_adcode": 450000,
        "province_id": 20
    },
    {
        "id": 227,
        "city_name": "贵港市",
        "city_adcode": 450800,
        "province_adcode": 450000,
        "province_id": 20
    },
    {
        "id": 228,
        "city_name": "玉林市",
        "city_adcode": 450900,
        "province_adcode": 450000,
        "province_id": 20
    },
    {
        "id": 229,
        "city_name": "百色市",
        "city_adcode": 451000,
        "province_adcode": 450000,
        "province_id": 20
    },
    {
        "id": 230,
        "city_name": "贺州市",
        "city_adcode": 451100,
        "province_adcode": 450000,
        "province_id": 20
    },
    {
        "id": 231,
        "city_name": "河池市",
        "city_adcode": 451200,
        "province_adcode": 450000,
        "province_id": 20
    },
    {
        "id": 232,
        "city_name": "来宾市",
        "city_adcode": 451300,
        "province_adcode": 450000,
        "province_id": 20
    },
    {
        "id": 233,
        "city_name": "崇左市",
        "city_adcode": 451400,
        "province_adcode": 450000,
        "province_id": 20
    },
    {
        "id": 234,
        "city_name": "海口市",
        "city_adcode": 460100,
        "province_adcode": 460000,
        "province_id": 21
    },
    {
        "id": 235,
        "city_name": "三亚市",
        "city_adcode": 460200,
        "province_adcode": 460000,
        "province_id": 21
    },
    {
        "id": 236,
        "city_name": "三沙市",
        "city_adcode": 460300,
        "province_adcode": 460000,
        "province_id": 21
    },
    {
        "id": 237,
        "city_name": "儋州市",
        "city_adcode": 460400,
        "province_adcode": 460000,
        "province_id": 21
    },
    {
        "id": 238,
        "city_name": "五指山市",
        "city_adcode": 469001,
        "province_adcode": 460000,
        "province_id": 21
    },
    {
        "id": 239,
        "city_name": "琼海市",
        "city_adcode": 469002,
        "province_adcode": 460000,
        "province_id": 21
    },
    {
        "id": 240,
        "city_name": "文昌市",
        "city_adcode": 469005,
        "province_adcode": 460000,
        "province_id": 21
    },
    {
        "id": 241,
        "city_name": "万宁市",
        "city_adcode": 469006,
        "province_adcode": 460000,
        "province_id": 21
    },
    {
        "id": 242,
        "city_name": "东方市",
        "city_adcode": 469007,
        "province_adcode": 460000,
        "province_id": 21
    },
    {
        "id": 243,
        "city_name": "定安县",
        "city_adcode": 469021,
        "province_adcode": 460000,
        "province_id": 21
    },
    {
        "id": 244,
        "city_name": "屯昌县",
        "city_adcode": 469022,
        "province_adcode": 460000,
        "province_id": 21
    },
    {
        "id": 245,
        "city_name": "澄迈县",
        "city_adcode": 469023,
        "province_adcode": 460000,
        "province_id": 21
    },
    {
        "id": 246,
        "city_name": "临高县",
        "city_adcode": 469024,
        "province_adcode": 460000,
        "province_id": 21
    },
    {
        "id": 247,
        "city_name": "白沙黎族自治县",
        "city_adcode": 469025,
        "province_adcode": 460000,
        "province_id": 21
    },
    {
        "id": 248,
        "city_name": "昌江黎族自治县",
        "city_adcode": 469026,
        "province_adcode": 460000,
        "province_id": 21
    },
    {
        "id": 249,
        "city_name": "乐东黎族自治县",
        "city_adcode": 469027,
        "province_adcode": 460000,
        "province_id": 21
    },
    {
        "id": 250,
        "city_name": "陵水黎族自治县",
        "city_adcode": 469028,
        "province_adcode": 460000,
        "province_id": 21
    },
    {
        "id": 251,
        "city_name": "保亭黎族苗族自治县",
        "city_adcode": 469029,
        "province_adcode": 460000,
        "province_id": 21
    },
    {
        "id": 252,
        "city_name": "琼中黎族苗族自治县",
        "city_adcode": 469030,
        "province_adcode": 460000,
        "province_id": 21
    },
    {
        "id": 253,
        "city_name": "重庆市",
        "city_adcode": 500100,
        "province_adcode": 500000,
        "province_id": 22
    },
    {
        "id": 254,
        "city_name": "成都市",
        "city_adcode": 510100,
        "province_adcode": 510000,
        "province_id": 23
    },
    {
        "id": 255,
        "city_name": "自贡市",
        "city_adcode": 510300,
        "province_adcode": 510000,
        "province_id": 23
    },
    {
        "id": 256,
        "city_name": "攀枝花市",
        "city_adcode": 510400,
        "province_adcode": 510000,
        "province_id": 23
    },
    {
        "id": 257,
        "city_name": "泸州市",
        "city_adcode": 510500,
        "province_adcode": 510000,
        "province_id": 23
    },
    {
        "id": 258,
        "city_name": "德阳市",
        "city_adcode": 510600,
        "province_adcode": 510000,
        "province_id": 23
    },
    {
        "id": 259,
        "city_name": "绵阳市",
        "city_adcode": 510700,
        "province_adcode": 510000,
        "province_id": 23
    },
    {
        "id": 260,
        "city_name": "广元市",
        "city_adcode": 510800,
        "province_adcode": 510000,
        "province_id": 23
    },
    {
        "id": 261,
        "city_name": "遂宁市",
        "city_adcode": 510900,
        "province_adcode": 510000,
        "province_id": 23
    },
    {
        "id": 262,
        "city_name": "内江市",
        "city_adcode": 511000,
        "province_adcode": 510000,
        "province_id": 23
    },
    {
        "id": 263,
        "city_name": "乐山市",
        "city_adcode": 511100,
        "province_adcode": 510000,
        "province_id": 23
    },
    {
        "id": 264,
        "city_name": "南充市",
        "city_adcode": 511300,
        "province_adcode": 510000,
        "province_id": 23
    },
    {
        "id": 265,
        "city_name": "眉山市",
        "city_adcode": 511400,
        "province_adcode": 510000,
        "province_id": 23
    },
    {
        "id": 266,
        "city_name": "宜宾市",
        "city_adcode": 511500,
        "province_adcode": 510000,
        "province_id": 23
    },
    {
        "id": 267,
        "city_name": "广安市",
        "city_adcode": 511600,
        "province_adcode": 510000,
        "province_id": 23
    },
    {
        "id": 268,
        "city_name": "达州市",
        "city_adcode": 511700,
        "province_adcode": 510000,
        "province_id": 23
    },
    {
        "id": 269,
        "city_name": "雅安市",
        "city_adcode": 511800,
        "province_adcode": 510000,
        "province_id": 23
    },
    {
        "id": 270,
        "city_name": "巴中市",
        "city_adcode": 511900,
        "province_adcode": 510000,
        "province_id": 23
    },
    {
        "id": 271,
        "city_name": "资阳市",
        "city_adcode": 512000,
        "province_adcode": 510000,
        "province_id": 23
    },
    {
        "id": 272,
        "city_name": "阿坝藏族羌族自治州",
        "city_adcode": 513200,
        "province_adcode": 510000,
        "province_id": 23
    },
    {
        "id": 273,
        "city_name": "甘孜藏族自治州",
        "city_adcode": 513300,
        "province_adcode": 510000,
        "province_id": 23
    },
    {
        "id": 274,
        "city_name": "凉山彝族自治州",
        "city_adcode": 513400,
        "province_adcode": 510000,
        "province_id": 23
    },
    {
        "id": 275,
        "city_name": "贵阳市",
        "city_adcode": 520100,
        "province_adcode": 520000,
        "province_id": 24
    },
    {
        "id": 276,
        "city_name": "六盘水市",
        "city_adcode": 520200,
        "province_adcode": 520000,
        "province_id": 24
    },
    {
        "id": 277,
        "city_name": "遵义市",
        "city_adcode": 520300,
        "province_adcode": 520000,
        "province_id": 24
    },
    {
        "id": 278,
        "city_name": "安顺市",
        "city_adcode": 520400,
        "province_adcode": 520000,
        "province_id": 24
    },
    {
        "id": 279,
        "city_name": "毕节市",
        "city_adcode": 520500,
        "province_adcode": 520000,
        "province_id": 24
    },
    {
        "id": 280,
        "city_name": "铜仁市",
        "city_adcode": 520600,
        "province_adcode": 520000,
        "province_id": 24
    },
    {
        "id": 281,
        "city_name": "黔西南布依族苗族自治州",
        "city_adcode": 522300,
        "province_adcode": 520000,
        "province_id": 24
    },
    {
        "id": 282,
        "city_name": "黔东南苗族侗族自治州",
        "city_adcode": 522600,
        "province_adcode": 520000,
        "province_id": 24
    },
    {
        "id": 283,
        "city_name": "黔南布依族苗族自治州",
        "city_adcode": 522700,
        "province_adcode": 520000,
        "province_id": 24
    },
    {
        "id": 284,
        "city_name": "昆明市",
        "city_adcode": 530100,
        "province_adcode": 530000,
        "province_id": 25
    },
    {
        "id": 285,
        "city_name": "曲靖市",
        "city_adcode": 530300,
        "province_adcode": 530000,
        "province_id": 25
    },
    {
        "id": 286,
        "city_name": "玉溪市",
        "city_adcode": 530400,
        "province_adcode": 530000,
        "province_id": 25
    },
    {
        "id": 287,
        "city_name": "保山市",
        "city_adcode": 530500,
        "province_adcode": 530000,
        "province_id": 25
    },
    {
        "id": 288,
        "city_name": "昭通市",
        "city_adcode": 530600,
        "province_adcode": 530000,
        "province_id": 25
    },
    {
        "id": 289,
        "city_name": "丽江市",
        "city_adcode": 530700,
        "province_adcode": 530000,
        "province_id": 25
    },
    {
        "id": 290,
        "city_name": "普洱市",
        "city_adcode": 530800,
        "province_adcode": 530000,
        "province_id": 25
    },
    {
        "id": 291,
        "city_name": "临沧市",
        "city_adcode": 530900,
        "province_adcode": 530000,
        "province_id": 25
    },
    {
        "id": 292,
        "city_name": "楚雄彝族自治州",
        "city_adcode": 532300,
        "province_adcode": 530000,
        "province_id": 25
    },
    {
        "id": 293,
        "city_name": "红河哈尼族彝族自治州",
        "city_adcode": 532500,
        "province_adcode": 530000,
        "province_id": 25
    },
    {
        "id": 294,
        "city_name": "文山壮族苗族自治州",
        "city_adcode": 532600,
        "province_adcode": 530000,
        "province_id": 25
    },
    {
        "id": 295,
        "city_name": "西双版纳傣族自治州",
        "city_adcode": 532800,
        "province_adcode": 530000,
        "province_id": 25
    },
    {
        "id": 296,
        "city_name": "大理白族自治州",
        "city_adcode": 532900,
        "province_adcode": 530000,
        "province_id": 25
    },
    {
        "id": 297,
        "city_name": "德宏傣族景颇族自治州",
        "city_adcode": 533100,
        "province_adcode": 530000,
        "province_id": 25
    },
    {
        "id": 298,
        "city_name": "怒江傈僳族自治州",
        "city_adcode": 533300,
        "province_adcode": 530000,
        "province_id": 25
    },
    {
        "id": 299,
        "city_name": "迪庆藏族自治州",
        "city_adcode": 533400,
        "province_adcode": 530000,
        "province_id": 25
    },
    {
        "id": 300,
        "city_name": "拉萨市",
        "city_adcode": 540100,
        "province_adcode": 540000,
        "province_id": 26
    },
    {
        "id": 301,
        "city_name": "日喀则市",
        "city_adcode": 540200,
        "province_adcode": 540000,
        "province_id": 26
    },
    {
        "id": 302,
        "city_name": "昌都市",
        "city_adcode": 540300,
        "province_adcode": 540000,
        "province_id": 26
    },
    {
        "id": 303,
        "city_name": "林芝市",
        "city_adcode": 540400,
        "province_adcode": 540000,
        "province_id": 26
    },
    {
        "id": 304,
        "city_name": "山南市",
        "city_adcode": 540500,
        "province_adcode": 540000,
        "province_id": 26
    },
    {
        "id": 305,
        "city_name": "那曲市",
        "city_adcode": 540600,
        "province_adcode": 540000,
        "province_id": 26
    },
    {
        "id": 306,
        "city_name": "阿里地区",
        "city_adcode": 542500,
        "province_adcode": 540000,
        "province_id": 26
    },
    {
        "id": 307,
        "city_name": "西安市",
        "city_adcode": 610100,
        "province_adcode": 610000,
        "province_id": 27
    },
    {
        "id": 308,
        "city_name": "铜川市",
        "city_adcode": 610200,
        "province_adcode": 610000,
        "province_id": 27
    },
    {
        "id": 309,
        "city_name": "宝鸡市",
        "city_adcode": 610300,
        "province_adcode": 610000,
        "province_id": 27
    },
    {
        "id": 310,
        "city_name": "咸阳市",
        "city_adcode": 610400,
        "province_adcode": 610000,
        "province_id": 27
    },
    {
        "id": 311,
        "city_name": "渭南市",
        "city_adcode": 610500,
        "province_adcode": 610000,
        "province_id": 27
    },
    {
        "id": 312,
        "city_name": "延安市",
        "city_adcode": 610600,
        "province_adcode": 610000,
        "province_id": 27
    },
    {
        "id": 313,
        "city_name": "汉中市",
        "city_adcode": 610700,
        "province_adcode": 610000,
        "province_id": 27
    },
    {
        "id": 314,
        "city_name": "榆林市",
        "city_adcode": 610800,
        "province_adcode": 610000,
        "province_id": 27
    },
    {
        "id": 315,
        "city_name": "安康市",
        "city_adcode": 610900,
        "province_adcode": 610000,
        "province_id": 27
    },
    {
        "id": 316,
        "city_name": "商洛市",
        "city_adcode": 611000,
        "province_adcode": 610000,
        "province_id": 27
    },
    {
        "id": 317,
        "city_name": "兰州市",
        "city_adcode": 620100,
        "province_adcode": 620000,
        "province_id": 28
    },
    {
        "id": 318,
        "city_name": "嘉峪关市",
        "city_adcode": 620200,
        "province_adcode": 620000,
        "province_id": 28
    },
    {
        "id": 319,
        "city_name": "金昌市",
        "city_adcode": 620300,
        "province_adcode": 620000,
        "province_id": 28
    },
    {
        "id": 320,
        "city_name": "白银市",
        "city_adcode": 620400,
        "province_adcode": 620000,
        "province_id": 28
    },
    {
        "id": 321,
        "city_name": "天水市",
        "city_adcode": 620500,
        "province_adcode": 620000,
        "province_id": 28
    },
    {
        "id": 322,
        "city_name": "武威市",
        "city_adcode": 620600,
        "province_adcode": 620000,
        "province_id": 28
    },
    {
        "id": 323,
        "city_name": "张掖市",
        "city_adcode": 620700,
        "province_adcode": 620000,
        "province_id": 28
    },
    {
        "id": 324,
        "city_name": "平凉市",
        "city_adcode": 620800,
        "province_adcode": 620000,
        "province_id": 28
    },
    {
        "id": 325,
        "city_name": "酒泉市",
        "city_adcode": 620900,
        "province_adcode": 620000,
        "province_id": 28
    },
    {
        "id": 326,
        "city_name": "庆阳市",
        "city_adcode": 621000,
        "province_adcode": 620000,
        "province_id": 28
    },
    {
        "id": 327,
        "city_name": "定西市",
        "city_adcode": 621100,
        "province_adcode": 620000,
        "province_id": 28
    },
    {
        "id": 328,
        "city_name": "陇南市",
        "city_adcode": 621200,
        "province_adcode": 620000,
        "province_id": 28
    },
    {
        "id": 329,
        "city_name": "临夏回族自治州",
        "city_adcode": 622900,
        "province_adcode": 620000,
        "province_id": 28
    },
    {
        "id": 330,
        "city_name": "甘南藏族自治州",
        "city_adcode": 623000,
        "province_adcode": 620000,
        "province_id": 28
    },
    {
        "id": 331,
        "city_name": "西宁市",
        "city_adcode": 630100,
        "province_adcode": 630000,
        "province_id": 29
    },
    {
        "id": 332,
        "city_name": "海东市",
        "city_adcode": 630200,
        "province_adcode": 630000,
        "province_id": 29
    },
    {
        "id": 333,
        "city_name": "海北藏族自治州",
        "city_adcode": 632200,
        "province_adcode": 630000,
        "province_id": 29
    },
    {
        "id": 334,
        "city_name": "黄南藏族自治州",
        "city_adcode": 632300,
        "province_adcode": 630000,
        "province_id": 29
    },
    {
        "id": 335,
        "city_name": "海南藏族自治州",
        "city_adcode": 632500,
        "province_adcode": 630000,
        "province_id": 29
    },
    {
        "id": 336,
        "city_name": "果洛藏族自治州",
        "city_adcode": 632600,
        "province_adcode": 630000,
        "province_id": 29
    },
    {
        "id": 337,
        "city_name": "玉树藏族自治州",
        "city_adcode": 632700,
        "province_adcode": 630000,
        "province_id": 29
    },
    {
        "id": 338,
        "city_name": "海西蒙古族藏族自治州",
        "city_adcode": 632800,
        "province_adcode": 630000,
        "province_id": 29
    },
    {
        "id": 339,
        "city_name": "银川市",
        "city_adcode": 640100,
        "province_adcode": 640000,
        "province_id": 30
    },
    {
        "id": 340,
        "city_name": "石嘴山市",
        "city_adcode": 640200,
        "province_adcode": 640000,
        "province_id": 30
    },
    {
        "id": 341,
        "city_name": "吴忠市",
        "city_adcode": 640300,
        "province_adcode": 640000,
        "province_id": 30
    },
    {
        "id": 342,
        "city_name": "固原市",
        "city_adcode": 640400,
        "province_adcode": 640000,
        "province_id": 30
    },
    {
        "id": 343,
        "city_name": "中卫市",
        "city_adcode": 640500,
        "province_adcode": 640000,
        "province_id": 30
    },
    {
        "id": 344,
        "city_name": "乌鲁木齐市",
        "city_adcode": 650100,
        "province_adcode": 650000,
        "province_id": 31
    },
    {
        "id": 345,
        "city_name": "克拉玛依市",
        "city_adcode": 650200,
        "province_adcode": 650000,
        "province_id": 31
    },
    {
        "id": 346,
        "city_name": "吐鲁番市",
        "city_adcode": 650400,
        "province_adcode": 650000,
        "province_id": 31
    },
    {
        "id": 347,
        "city_name": "哈密市",
        "city_adcode": 650500,
        "province_adcode": 650000,
        "province_id": 31
    },
    {
        "id": 348,
        "city_name": "昌吉回族自治州",
        "city_adcode": 652300,
        "province_adcode": 650000,
        "province_id": 31
    },
    {
        "id": 349,
        "city_name": "博尔塔拉蒙古自治州",
        "city_adcode": 652700,
        "province_adcode": 650000,
        "province_id": 31
    },
    {
        "id": 350,
        "city_name": "巴音郭楞蒙古自治州",
        "city_adcode": 652800,
        "province_adcode": 650000,
        "province_id": 31
    },
    {
        "id": 351,
        "city_name": "阿克苏地区",
        "city_adcode": 652900,
        "province_adcode": 650000,
        "province_id": 31
    },
    {
        "id": 352,
        "city_name": "克孜勒苏柯尔克孜自治州",
        "city_adcode": 653000,
        "province_adcode": 650000,
        "province_id": 31
    },
    {
        "id": 353,
        "city_name": "喀什地区",
        "city_adcode": 653100,
        "province_adcode": 650000,
        "province_id": 31
    },
    {
        "id": 354,
        "city_name": "和田地区",
        "city_adcode": 653200,
        "province_adcode": 650000,
        "province_id": 31
    },
    {
        "id": 355,
        "city_name": "伊犁哈萨克自治州",
        "city_adcode": 654000,
        "province_adcode": 650000,
        "province_id": 31
    },
    {
        "id": 356,
        "city_name": "塔城地区",
        "city_adcode": 654200,
        "province_adcode": 650000,
        "province_id": 31
    },
    {
        "id": 357,
        "city_name": "阿勒泰地区",
        "city_adcode": 654300,
        "province_adcode": 650000,
        "province_id": 31
    },
    {
        "id": 358,
        "city_name": "胡杨河市",
        "city_adcode": 659000,
        "province_adcode": 650000,
        "province_id": 31
    },
    {
        "id": 359,
        "city_name": "石河子市",
        "city_adcode": 659001,
        "province_adcode": 650000,
        "province_id": 31
    },
    {
        "id": 360,
        "city_name": "阿拉尔市",
        "city_adcode": 659002,
        "province_adcode": 650000,
        "province_id": 31
    },
    {
        "id": 361,
        "city_name": "图木舒克市",
        "city_adcode": 659003,
        "province_adcode": 650000,
        "province_id": 31
    },
    {
        "id": 362,
        "city_name": "五家渠市",
        "city_adcode": 659004,
        "province_adcode": 650000,
        "province_id": 31
    },
    {
        "id": 363,
        "city_name": "北屯市",
        "city_adcode": 659005,
        "province_adcode": 650000,
        "province_id": 31
    },
    {
        "id": 364,
        "city_name": "铁门关市",
        "city_adcode": 659006,
        "province_adcode": 650000,
        "province_id": 31
    },
    {
        "id": 365,
        "city_name": "双河市",
        "city_adcode": 659007,
        "province_adcode": 650000,
        "province_id": 31
    },
    {
        "id": 366,
        "city_name": "可克达拉市",
        "city_adcode": 659008,
        "province_adcode": 650000,
        "province_id": 31
    },
    {
        "id": 367,
        "city_name": "昆玉市",
        "city_adcode": 659009,
        "province_adcode": 650000,
        "province_id": 31
    },
    {
        "id": 368,
        "city_name": "台北市",
        "city_adcode": 710100,
        "province_adcode": 710000,
        "province_id": 32
    },
    {
        "id": 369,
        "city_name": "高雄市",
        "city_adcode": 710200,
        "province_adcode": 710000,
        "province_id": 32
    },
    {
        "id": 370,
        "city_name": "新北市",
        "city_adcode": 710300,
        "province_adcode": 710000,
        "province_id": 32
    },
    {
        "id": 371,
        "city_name": "台中市",
        "city_adcode": 710400,
        "province_adcode": 710000,
        "province_id": 32
    },
    {
        "id": 372,
        "city_name": "台南市",
        "city_adcode": 710500,
        "province_adcode": 710000,
        "province_id": 32
    },
    {
        "id": 373,
        "city_name": "桃园市",
        "city_adcode": 710600,
        "province_adcode": 710000,
        "province_id": 32
    },
    {
        "id": 374,
        "city_name": "基隆市",
        "city_adcode": 719001,
        "province_adcode": 710000,
        "province_id": 32
    },
    {
        "id": 375,
        "city_name": "新竹市",
        "city_adcode": 719002,
        "province_adcode": 710000,
        "province_id": 32
    },
    {
        "id": 376,
        "city_name": "嘉义市",
        "city_adcode": 719003,
        "province_adcode": 710000,
        "province_id": 32
    },
    {
        "id": 377,
        "city_name": "新竹县",
        "city_adcode": 719004,
        "province_adcode": 710000,
        "province_id": 32
    },
    {
        "id": 378,
        "city_name": "宜兰县",
        "city_adcode": 719005,
        "province_adcode": 710000,
        "province_id": 32
    },
    {
        "id": 379,
        "city_name": "苗栗县",
        "city_adcode": 719006,
        "province_adcode": 710000,
        "province_id": 32
    },
    {
        "id": 380,
        "city_name": "彰化县",
        "city_adcode": 719007,
        "province_adcode": 710000,
        "province_id": 32
    },
    {
        "id": 381,
        "city_name": "云林县",
        "city_adcode": 719008,
        "province_adcode": 710000,
        "province_id": 32
    },
    {
        "id": 382,
        "city_name": "南投县",
        "city_adcode": 719009,
        "province_adcode": 710000,
        "province_id": 32
    },
    {
        "id": 383,
        "city_name": "嘉义县",
        "city_adcode": 719010,
        "province_adcode": 710000,
        "province_id": 32
    },
    {
        "id": 384,
        "city_name": "屏东县",
        "city_adcode": 719011,
        "province_adcode": 710000,
        "province_id": 32
    },
    {
        "id": 385,
        "city_name": "台东县",
        "city_adcode": 719012,
        "province_adcode": 710000,
        "province_id": 32
    },
    {
        "id": 386,
        "city_name": "花莲县",
        "city_adcode": 719013,
        "province_adcode": 710000,
        "province_id": 32
    },
    {
        "id": 387,
        "city_name": "澎湖县",
        "city_adcode": 719014,
        "province_adcode": 710000,
        "province_id": 32
    },
    {
        "id": 388,
        "city_name": "香港",
        "city_adcode": 810000,
        "province_adcode": 810000,
        "province_id": 33
    },
    {
        "id": 389,
        "city_name": "澳门",
        "city_adcode": 820000,
        "province_adcode": 820000,
        "province_id": 34
    }
	]
	json_str = json.dumps(params)
	# 将 JSON 对象转换为 Python 字典
	params_json = json.loads(json_str)

	articleText = '福利彩票'

	for item in params_json:
		cityName = item['city_name']
		cityCode = item['city_adcode']
		print(cityName,cityCode)
		time.sleep(10)
		newThread = webThread(1, "Thread-1", 1, cityName,cityCode, articleText)
		newThread.start()


