from langchain_openai import ChatOpenAI
# from langchain_anthropic import ChatAnthropic
# from langchain_google_genai import ChatGoogleGenerativeAI

def get_llm(model: str, **kwargs):
    return ChatOpenAI(model=model, **kwargs)
