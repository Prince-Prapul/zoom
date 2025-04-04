import requests
import json

url = "http://localhost:8000/generate_mcq" 

# Example text input
input_data = {
    "text": "In the second project, we will develop another cloud application using PaaS resources. Specifically, we will build this application using AWS Lambda and other supporting services from AWS. AWS Lambda is the first and currently the most widely used function-based serverless computing service. We will develop a more sophisticated application than Project 1, as we are now more experienced with cloud programming and PaaS also makes it easier for us to develop in the cloud. This project will also give us the opportunity to learn a few more important cloud services, including AWS Lambda and Elastic Container Registry (ECR).Our PaaS application will provide face recognition as a service on video frames streamed from the clients (e.g., security cameras). This is an important cloud service to many users, and the technologies and techniques that we learn will be useful for us to build many others in the future.",
    "num_questions": 5
}

# Convert the input data to JSON
json_data = json.dumps(input_data)

# Set the headers for a JSON request
headers = {'Content-Type': 'application/json'}

try:
    # Send the POST request
    response = requests.post(url, data=json_data, headers=headers)

    # Check the response status code
    if response.status_code == 200:
        print("POST request successful!")
        print("Response JSON:")
        print(json.dumps(response.json(), indent=4))
    else:
        print(f"POST request failed with status code: {response.status_code}")
        print("Response text:")
        print(response.text)

except requests.exceptions.ConnectionError as e:
    print(f"Error: Could not connect to the server at {url}. Please ensure the server is running.")
    print(f"Details: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")