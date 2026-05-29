# from app.summarizer.ai_summarizer import generate_summaries


# def run_pipeline():

#     print("\nStarting AI Current Affairs Pipeline...\n")

#     final_summary = generate_summaries()

#     print("\n" + "=" * 100)

#     print("\nFINAL SUMMARY:\n")

#     print(final_summary)


# if __name__ == "__main__":

#     run_pipeline()


# from app.summarizer.ai_summarizer import generate_summaries

# from app.storage.save_json import save_summary


# def run_pipeline():

#     print("\n🚀 Starting AI Current Affairs Pipeline...\n")

#     final_summary = generate_summaries()

#     # Save summary
#     save_summary(final_summary)

#     print("\n" + "=" * 100)

#     print("\n✅ PIPELINE COMPLETED SUCCESSFULLY\n")


# if __name__ == "__main__":

#     run_pipeline()

from app.summarizer.ai_summarizer import generate_summaries

from app.storage.save_json import save_summary


def run_pipeline():

    print("\n🚀 Starting AI Current Affairs Pipeline...\n")

    summarized_articles = generate_summaries()

    save_summary(summarized_articles)

    print("\n✅ PIPELINE COMPLETED SUCCESSFULLY")


if __name__ == "__main__":

    run_pipeline()