I want to generate a tool that allows us to ask a question, whether medical or scientific, and have the tool look up in pubmed relevant papers in pubmed to answer the question.  To ensure that we are going according to scientific consensus, we want the query to be weighted towards more highly cited papers than papers with low citations, while also ensuring relevance.
I want the system to be run locally, so the database is local, and the model we are using is local.

Please research this problem, formulate an implementation plan.  Some questions:
  -  Are we gonna use RAG and a vector database?
  -  Are we gonna use a tri-letter index for quick search for important terms/words?
  -  A combination?
  -  Any other ideas welcome

Launch a subagent with only read access to critique the plan.  Edit the plan in response to the critique.