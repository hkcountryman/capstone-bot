#Option 1
import json
json_person = '{"name": "Kevin", "age": 100, "hobbies": ["video games", "ultimate frisbee"], "appearance": {"hair_color": "black","weight": "350"}}'
# JSON object -> Python dictionary
person_dictionary = json.loads(json_person)
person_dictionary.get("age") #100

# Python object -> JSON string
json_person = json.dumps(person_dictionary)
# Pretty Print
json.dumps(person_dictionary, sort_keys=True, indent=4)
# sort_keys is optional
# indent should be 2 or 4

# Write to JSON File
with open ("example.json", "w") as file:
	file.write(json_person)

# Read from JSON file
with open("example.json", "r") as file:
	json_content = json.loads(file.read())


#Option 2
import jsonpickle
python_obj = Thing('Example String')

# Python object -> JSON string
pickled = jsonpickle.encode(python_obj)
# pickled = 
#{
	#"py/object": {
		#"samples.Thing", 
		#"name": "Example String", 
		#"child": null
	#}
#}

# JSON string -> Python obejct
unpickled = jsonpickle.decode(pickled)
str(unpickled.name) #Example String