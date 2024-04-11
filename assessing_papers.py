#importing libraries and setting up API
from openai import OpenAI
import pandas as pd
import json
# with open('key.txt', 'r') as file:
#     key = file.read()
# client = OpenAI(api_key = key)
# Initialize the OpenAI client
client = OpenAI()
client.api_key = os.getenv("OPENAI_API_KEY")

#Importing the CSV and adding the titles and abstracts to lists to subsequently use in the API function

# Load the CSV file.
# The file should have the title in the first column and the abstract in the second column and no header.
# Since the CSV has no header, we specify header=None and assign the column names manually.
#df = pd.read_csv('papers.csv', header=None, names=['Title', 'Abstract'])
df = pd.read_csv('Papers with abstracts.csv')


# Add the 'Concatenated' column by concatenating the 'title' and 'abstract' columns with the desired format.
df['Concatenated'] = "<title>" + df['Title'] + "</title>\n\n<abstract>" + df['Abstract'] + "</abstract>"

# Create the 'content' list containing all the rows of the 'Concatenated' column.
#This is a mix of the Title and Abstract that we'll give to the API.
content = df['Concatenated'].tolist()

#Create individual lists for the titles and abstracts
titles = df['Title'].tolist()
abstracts = df['Abstract'].tolist()

#Prompt for what OpenAI is meant to do
with open('prompt.txt', 'r') as file:
    prompt = file.read() 

#The API bit

#Function that is designed to take the content list from above
#The function should output a judgement on what the focus of each paper is and an explanation for that
def analyze_paper(item,prompt,version):
    response = client.chat.completions.create(
      model=version,
      messages=[
        {
          "role": "system",
          "content": prompt
        },
        {
          "role": "user",
          "content": item
        }
      ],
      temperature=1,
      max_tokens=256,
      top_p=1,
      frequency_penalty=0,
      presence_penalty=0,
    )
    
    APIoutput = response.choices[0].message.content
    response_dict = json.loads(APIoutput)
    focus = response_dict['categorization']
    explanation = response_dict['reasoning']
    
    return(focus, explanation)

#Runs the function and adds the two outputs to separate lists
focuses = []
explanations = []
for item in content:
    value1, value2 = analyze_paper(item,prompt,"gpt-3.5-turbo")
    focuses.append(value1)
    explanations.append(value2)
    
#models to choose from: gpt-4-turbo-preview gpt-3.5-turbo

#Combining all the lists into a dataframe
df = pd.DataFrame({
    'Title': titles,
    'Abstract': abstracts,
    'Safety focus': focuses,
    'Explanation': explanations
})

df.to_csv('final_output.csv', index=False)