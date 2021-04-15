#primary format of response: JSON
import json

#Flask import
from flask import Flask,request

#MySQL
import mysql.connector

#Redis
import redis

#MongoDB
import pymongo

#Neo4J 
from neo4j import GraphDatabase


app = Flask(__name__)

class DatabaseConnector:
	# Used to connect to various databases
	def __init__(self):
		#Class constructor 
		#Run all connection creation
		self.create_sql_connection()
		self.create_redis_connection()
		self.create_mongo_connection()
		self.create_neo4j_connection()

	def create_sql_connection(self):
		#create an SQL connection
		self.mysql_db = mysql.connector.connect(
			host = "localhost",
			user="ninadnaik",
			password="ninad123",
			database="symbichat"
		)

	def create_redis_connection(self):
		# create a redis connection
		self.redis_db = redis.Redis(host='localhost', port=6379, db=0)
		

	def create_mongo_connection(self):
		# create a mongodb connection
		mongodb_client = pymongo.MongoClient("mongodb://localhost:27017/")
		self.mongodb_db = mongodb_client['symbichat']

	def create_neo4j_connection(self):
		# create a neo4j connection
		self.graph_db = GraphDatabase.driver('bolt:0.0.0.0:7687',auth=("neo4j","ninad123"))
		self.session = self.graph_db.session();

	def sql_query(self,id):
		#get user information from an SQL db using id
		#return: user information
		my_cursor = self.mysql_db.cursor()
		my_cursor.execute("SELECT fname, lname, email FROM PERSON WHERE id = "+id)
		myresult = my_cursor.fetchall()
		return myresult;

	def sql_query_all_students(self):
		#get user information from an SQL db using id
		#return: user information
		my_cursor = self.mysql_db.cursor()
		my_cursor.execute("SELECT id, fname, lname, email FROM PERSON")
		myresult = my_cursor.fetchall()
		return myresult;


	def redis_get_query(self,team_name):
		#return: team information
		result = self.redis_db.hgetall(team_name)
		if result == None:
			result = ""
		return str(result)

	def redis_set_query(self,name,member1,member2,member3,desc):
		#this function makes a hashmap in redis
		try:
			# hset(hash_name,key,value) 
			self.redis_db.hset(name, "member1", member1)
			self.redis_db.hset(name, "member2", member2)
			self.redis_db.hset(name, "member3", member3)
			self.redis_db.hset(name, "desc", desc)
			return "Success"
		except Exception as e:
			return "Failure"

	def mongodb_get_query(self,id):
		#get user comments using id
		#return: result with all comments of user with id

		#get the mongodb collection
		mongodb_col = self.mongodb_db['comments']
		result = ""
		# get all data
		if id=="":
			for x in mongodb_col.find({},{"fname":1,"lname":1,"comment":1}):
				result+=str(x)
		#get user with the particular ID
		else:
			for x in mongodb_col.find({"uid":int(id)},{"fname":1,"lname":1,"comment":1}):
				result+=str(x)
		return result

	def mongodb_set_query(self,id,fname,lname,comment):
		#set a comment for user with id
		#return: object id to check if it works or not
		mongodb_col = self.mongodb_db['comments']
		result = mongodb_col.insert({"uid":int(id),"fname":fname,"lname":lname,"comment":comment})
		return result

	def neo4j_get_query(self,tx,interest):
		#get people who have a particular keyword in their interests 
		data = []
		for record in tx.run("MATCH (person:Person)-[:has]->(interest:Interest) "+
			"WHERE toLower(interest.name) CONTAINS toLower($interest) "+
			"RETURN person,interest",interest = interest):
			node = {
				'person' : record['person']['uid'],
				'name': record['person']['fname']+" "+record['person']['lname'],
				'interest': record['interest']['name']
			}
			data.append(node)
		return data

	def neo4j_set_query(self,tx,uid,fname,lname,interest_name):
		#assign an interest to a person
		result = tx.run("MERGE (p:Person{uid:$uid,fname:$fname,lname:$lname}) " +
						"MERGE (i:Interest{name:toLower($interest_name)}) " +
						"MERGE (p)-[:has]->(i) "+
						"RETURN p,i",uid=uid,fname=fname,lname=lname,interest_name=interest_name)
		return result


database_connector = DatabaseConnector()

	
@app.route('/')
def hello_world():
	return "Server alive"

@app.route('/mysql/<id>')
def mysql_get_student(id):
	result = database_connector.sql_query(id);
	return str(result)

@app.route('/mysql_all/')
def mysql_get_all_student():
	result = database_connector.sql_query_all_students();
	return str(result)

@app.route('/redis_get/<name>')
def redis_get_team_description(name):
	team_key = "team:"+name
	result = database_connector.redis_get_query(team_key)
	return result

@app.route('/redis_set/<name>/<member1>/<member2>/<member3>/<desc>')
def redis_set_team_description(name,member1,member2,member3,desc):
	team_key = "team:"+name
	result = database_connector.redis_set_query(team_key,member1,member2,member3,desc)
	return str(result)

@app.route('/mongodb_get/<id>')
def mongodb_get_comment(id):
	result = database_connector.mongodb_get_query(id)
	return str(result)

@app.route('/mongodb_get/')
def mongodb_get_all_comment():
	result = database_connector.mongodb_get_query("")
	return str(result)


@app.route('/mongodb_set/<id>/<fname>/<lname>/<comment>')
def mongodb_set_comment(id,fname,lname,comment):
	result = database_connector.mongodb_set_query(id,fname,lname,comment)
	if result is not None or result != "":
		return {"status":"Success"}
	else:
		return {"status":"Failure"} 

@app.route('/neo4j_set/<uid>/<fname>/<lname>/<interest>')
def neo4j_set_interest(uid,fname,lname,interest):
	records = database_connector.session.write_transaction(database_connector.neo4j_set_query,uid,fname,lname,interest)
	if(str(records)!=""):
		return "Success"
	else:
		return "Failure"	

@app.route('/neo4j_get/<interest>')
def neo4j_get_interest(interest):
	records = database_connector.session.read_transaction(database_connector.neo4j_get_query,interest)
	return str(records)

if __name__ == '__main__':
	app.run(debug=True,host='0.0.0.0',port=5000)