
# A runbook is an operational guide for dealing with a specific type of problem.
# We have added 3 runbooks


# Without RAG, Claude has to reason based primarily on:
# incident + MCP data
#
# It might say:
# The payment provider appears unavailable. Check connectivity, DNS, TLS, and consider failover.
#
# That's reasonable, but imagine your company has specific procedures:
# For payment provider failures, check X, then Y. If error rate exceeds 95%, enable circuit breaker. If provider A is unavailable, route to provider B.
#
# That company-specific knowledge isn't necessarily in Claude's general training.
# That's what your runbooks provide. Retrieval-Augmented Generation

import os
import chromadb
# os lets Python work with files/directories.
# chromadb is your vector database.
# Chroma uses an embedding model to convert the text into numerical vectors.
# So your runbook text becomes something that can be compared based on semantic similarity.
# Conceptually:
# "Payment provider timeout"
#           ↓
#    embedding model
#           ↓
# [0.12, -0.43, 0.81, ...]


# rel path to runbooks dir
RUNBOOK_DIR = os.path.join(
    os.path.dirname(__file__),
    "runbooks"
)

# This creates/opens a persistent Chroma database.
# The important word is persistent.
# We're not just storing the vectors temporarily in memory.
# Chroma saves them to: chroma_db/
# so they can be reused the next time your application starts.
client = chromadb.PersistentClient(
    path=os.path.join(
        os.path.dirname(__file__),
        "chroma_db"
    )
)


# A Chroma collection is roughly analogous to a table/database collection where related documents are stored.
# We're telling Chroma:
# "Create a collection where I'm going to store my incident runbooks."
collection = client.get_or_create_collection(
    name="incident-runbooks"
)

# In this method, we're essentially creating:
# ID                              DOCUMENT
# ────────────────────────────────────────────────
# payment-provider-timeout.md     # Payment Provider Timeout...
# payment-service-down.md         # Payment Service Down...
# high-error-rate.md              # High Error Rate...
def load_runbooks():
    documents = []
    ids = []

    # This looks through: runbooks/
    for filename in os.listdir(RUNBOOK_DIR):
        # Only load Markdown files.
        if filename.endswith(".md"):
            path = os.path.join(RUNBOOK_DIR, filename)

            with open(path, "r") as file:
                # reads the entire Markdown file and puts its contents into documents
                documents.append(file.read())

            ids.append(filename)

    return documents, ids


def initialize_rag():
    documents, ids = load_runbooks()

    # upsert means:
    # Insert this document if it doesn't exist, or update it if it already exists.
    # hat's useful because you can modify payment-provider-timeout.md
    # and rerun your application without creating duplicate documents.
    collection.upsert(
        documents=documents,
        ids=ids
    )

# Find the two runbooks most relevant to this query.
# Chroma converts the input query into an embedding too:
# query
#  ↓
# embedding model
#  ↓
# [0.10, -0.40, 0.79, ...]
# Then it compares that against the vectors for your runbooks.
def retrieve_runbook(query: str, n_results: int = 2):
    results = collection.query(
        query_texts=[query],
        n_results=n_results
    )

    return results["documents"][0]

# temp code to test
if __name__ == "__main__":
    initialize_rag()

    results = retrieve_runbook(
        "Payment provider is timing out and latency is extremely high"
    )

    for result in results:
        print("\n--- RUNBOOK ---")
        print(result)



# Why we've added this:
# So the agent won't just ask Claude:
#
# "What should I do?"
#
# It'll effectively ask:
#
# "Given this incident and the evidence I've gathered, what does our operational knowledge say we should do?"