import os
import dotenv
import pandas as pd

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.tools import tool
from langchain.globals import set_debug

# Pandas agents
from langchain.agents.agent_types import AgentType
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain_openai import ChatOpenAI

from data.carparking import CarPark

# set_debug(True)
dotenv.load_dotenv()

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
DATAMALL_API_KEY = os.environ.get("DATAMALL_API_KEY")

# https://python.langchain.com/docs/integrations/toolkits/pandas


@tool
def use_carpark_api():
    """
    Retrieves real-time carpark availability with an API call.

    Description of columns:
    CarParkID: String column, [description]
    Area: [type] [description]
    ...
    """
    CarPark = CarPark(DATAMALL_API_KEY)
    return CarPark.response


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

        df = pd.read_csv("carparking.csv")
        self.agent = create_pandas_dataframe_agent(
            ChatOpenAI(temperature=0, model="gpt-3.5-turbo-0613"),
            df,
            verbose=True,
            agent_type=AgentType.OPENAI_FUNCTIONS,
            agent_executor_kwargs={"handle_parsing_errors": True},
        )

    def query_agent(self, query):
        answer = self.agent.run(query)
        # chain = prompt | agent
        # answer = chain.invoke({"input": "Which area has the most available lots?"})
        return answer
