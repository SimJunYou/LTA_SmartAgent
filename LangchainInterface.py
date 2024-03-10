import os
import dotenv
import pandas as pd

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.tools import tool
from langchain.globals import set_debug

from langchain.agents.agent_types import AgentType
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain_community.agent_toolkits import create_sql_agent
from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI

from data.carparking import CarPark
from aws import AWS
from database import Database

# set_debug(True)
dotenv.load_dotenv()

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
DATAMALL_API_KEY = os.environ.get("DATAMALL_API_KEY")

# https://python.langchain.com/docs/integrations/toolkits/pandas


class LangchainInterface:
    def __init__(self):
        self.llm = ChatOpenAI(openai_api_key=OPENAI_API_KEY)
        self.output_parser = StrOutputParser()
        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a Singapore Land Transport Authority agent tasked to answer any queries posed by users. Below is such a query:",
                ),
                ("user", "{input}"),
            ]
        )

        # aws = AWS()
        # instance_id = aws.rds.listInstance()
        # endpoint, port = aws.rds.readInstance(instance_id)
        database = Database()
        db = SQLDatabase.from_uri(database.connection_str)
        # self.agent = create_pandas_dataframe_agent(
        #     ChatOpenAI(temperature=0, model="gpt-3.5-turbo-0613"),
        #     df,
        #     verbose=True,
        #     agent_type=AgentType.OPENAI_FUNCTIONS,
        #     agent_executor_kwargs={"handle_parsing_errors": True},
        # )

        self.agent = create_sql_agent(
            ChatOpenAI(temperature=0, model="gpt-3.5-turbo-0613"),
            db=db,
            agent_type="openai-tools",
            verbose=True,
        )

    def query_agent(self, query):
        answer = self.agent.invoke({"input": query})
        # chain = prompt | agent
        # answer = chain.invoke({"input": "Which area has the most available lots?"})
        return answer


if __name__ == "__main__":
    lc = LangchainInterface()
    lc.query_agent("How many available lots in total are there at Suntec City?")
