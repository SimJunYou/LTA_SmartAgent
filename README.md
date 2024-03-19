# LTA Smart Agent

## Development

Create a virtual environment with Python 3.10 and install required libraries from `requirements.txt` using Conda:
```bash
# If you do not have an environment made
conda create --name <envname> python=3.10 --file requirements.txt  

# If environment exists and is activated
conda install --file requirements.txt  
```

If that is not working, run the following command to install the essential libraries from Pip.

```bash
pip install pandas numpy bs4 langchain langchain-experimental langchain-openai python-telegram-bot python-dotenv tabulate boto3 sqlalchemy psycopg2-binary 
```
