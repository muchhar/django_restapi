from django.conf import settings
from django.contrib.auth import get_user_model
from api.models import User,Product,Sales,IncomingInventory,UserInventory,OldIncomingInventory,OldUserInventory,DailyInventoryMetrics
from datetime import datetime, timedelta
import pytz
import time

from decimal import Decimal
from django.db.models import Sum, Q
def update_incoming():
	est = pytz.timezone('America/New_York')
	now_est = datetime.now(est)

	current_date = now_est.date()
	incoming = IncomingInventory.objects.all()
	hold_l=[]
	for i in incoming:
		if str(i.arrival_date)==str(current_date):
			inventory, created = UserInventory.objects.get_or_create(
                user=i.user,
                product=i.product,
                defaults={'quantity': i.quantity}
            )
			if not created:
				inventory.quantity += i.quantity
				inventory.save()
			inventory2, created = OldIncomingInventory.objects.get_or_create(
                user=i.user,
                product=i.product,
                quantity=i.quantity,
				arrival_date = i.arrival_date
            )
			
			hold_l.append(i)
			
	for v in hold_l:
		v.delete()
def update_oldOnHand():
	est = pytz.timezone('America/New_York')
	now_est = datetime.now(est)

	current_date = now_est.date()
	inventry = UserInventory.objects.all()
	
	for i in inventry:
		inventory2, created = OldUserInventory.objects.get_or_create(
			
                user=i.user,
                product=i.product,
                quantity=i.quantity,
				date= current_date
            )
	pass
def get_onHand(user,product,date):
	return OldUserInventory.objects.filter(
            user=user,
            product=product,
            date=date
        ).aggregate(total=Sum('quantity'))['total'] or 0
def get_leadtime(product):
	for i in Product.objects.all():
		if(i==product):
			return i.lead_time
	return 0
def schedule_api():
	est = pytz.timezone('America/New_York')
	now_est = datetime.now(est)

	current_date = now_est.date()
	hour = now_est.hour
	minute = now_est.minute
	if hour<11:
		return
	update_incoming()
	update_oldOnHand() #before if not cal todays+ inventory
	users = User.objects.all()
	products = Product.objects.all()
	sales = Sales.objects.all()
	incoming = IncomingInventory.objects.all()
	
	date_list = [(current_date - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]

	if(str(hour)=="23" and str(minute)=="59"):
		pass
	for user in users:
		main_data={}

		for product in products:
			main_data[product]={"sales":{},"lead":product.lead_time,"incoming":{},"onhand":{}}
			
			for ideal_date in date_list:
				main_data[product]["sales"][ideal_date]=0
				main_data[product]["incoming"][ideal_date]=get_incoming_inventory(user=user,product=product,date=ideal_date)
				main_data[product]["onhand"][ideal_date]=get_onHand(user=user,product=product,date=ideal_date)
			for sale in sales:
				if sale.product == product and sale.user==user:
					if str(sale.sale_date) in date_list:
						main_data[product]["sales"][str(sale.sale_date)]+=sale.quantity
			
		
		predict_next(main_data=main_data,user=user)
	
def get_incoming_inventory( user, product, date):
        """Get incoming inventory for a specific date"""
        return OldIncomingInventory.objects.filter(
            user=user,
            product=product,
            arrival_date=date
        ).aggregate(total=Sum('quantity'))['total'] or 0

def predict_next(main_data,user):
	est = pytz.timezone('America/New_York')
	now_est = datetime.now(est)

	current_date = now_est.date()
	next_14_days = [(current_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(1, 15)]
	for i in main_data.keys():
		date_wise_projection={}
		for dt in next_14_days:
			lead=get_leadtime(i)
			fc=calculate_forecast(product=i,date=dt,main_data=main_data,next_days=next_14_days)
			inc=get_incoming_inventory(user=user,product=i,date=dt)
			op=get_orderPoint(product=i,date=dt,main_data=main_data,lead_time=get_leadtime(i))
			poh=get_projectedOnhand(po=True,main_data=main_data,fc=fc,inc=inc,to_date=dt,product=i,hist=date_wise_projection,lead=lead)
			soq= get_soq(poh=poh,op=op)
			planned_arrivel=get_projectedOnhand(po=False,main_data=main_data,fc=fc,inc=inc,to_date=dt,product=i,hist=date_wise_projection,lead=lead)
			date_wise_projection[dt]=[poh,soq]
			final_data={
					"Date":dt,
			   		"user":user,
					"product":i,
					"Is_projection":True,
					"sales":0,
					"On_hand":0,
					"incoming":inc,
					"Lead_Time":lead,
					
					"Forecast":fc,
					"Order_Point":op,
					
					"projected_on_hand":poh,
					"soq":soq,
					"planned_arrivel":planned_arrivel
					
					}
			savedb(final_data)
			
def savedb(data):
	print(data)
	if(data['Order_Point']==0 and data['Forecast']==0 and data['soq']==0):
		return
	max_retries = 5
	for attempt in range(max_retries):
		try:
			metrics, created = DailyInventoryMetrics.objects.update_or_create(	
			user = data['user'],
			product = data['product'],
			date = data['Date'],
			is_projection = True,
			# Core metrics
			sales = data['sales'],
			on_hand = data['On_hand'],
			incoming = data['incoming'],
			# Calculated metrics
			order_point = data['Order_Point'],
			lead_time_days = data['Lead_Time'],
			forecast = data['Forecast'],
			projected_on_hand = data['projected_on_hand'],
			soq = data['soq'],
			planned_arrival = data['planned_arrivel']
				)
			return
		except:
			time.sleep(2)
			pass
def get_projectedOnhand(po,main_data,fc,inc,to_date,product,hist,lead):

	date_obj = datetime.strptime(to_date, "%Y-%m-%d").date()
	previous_day = date_obj - timedelta(days=1)
	est = pytz.timezone('America/New_York')
	now_est = datetime.now(est)

	if(previous_day== now_est.date()):
		print(main_data[product]['onhand'][str(previous_day)])
		if po:
			return main_data[product]['onhand'][str(previous_day)] - fc + inc + 0
		else:
			return 0
	else:
		x = date_obj - timedelta(days=lead)
		arriaval =0
		if x in hist:
			arriaval = hist[x][1]
		if po:
			return hist[str(previous_day)][0] - fc + inc + arriaval
		else:
			return arriaval	
def get_soq(poh,op):
	if poh<op:
		return op-poh
	else: 
		return 0

def calculate_forecast(product,date,main_data,next_days):
	all_data=[]
	for i in main_data[product]["sales"].keys():
		all_data.append(main_data[product]["sales"][i])
	for i in next_days:
		print('###########')
		print(all_data)
		vel =sum(all_data[:7])/7
		all_data.insert(0,vel)
		if(i==date):
			return round(vel,2)
	pass	
def get_orderPoint(product,date,main_data,lead_time):
	est = pytz.timezone('America/New_York')
	now_est = datetime.now(est)

	current_date = now_est.date()
	next_x_days = [(current_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(1, 15+lead_time)]
	
	all_data=[]
	all_date=[]
	for i in main_data[product]["sales"].keys():
		all_data.append(main_data[product]["sales"][i])
		all_date.append(i)
	for i in next_x_days:
		vel =sum(all_data[:7])/7
		all_data.insert(0,vel)
		all_date.insert(0,i)
	x = all_date.index(date)
	total_point=0
	for i in range(lead_time):
		total_point+=all_data[x]
		x-=1
	return round(total_point,2)
	
