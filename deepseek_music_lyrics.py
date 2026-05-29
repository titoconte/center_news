'''
Script to use deepseek API to get music lyrics

1 - get the list of music in excel file and call for deepseek API
2 - save the lyrics in a txt file

'''


from openai import OpenAI
import time
import pandas as pd


def get_lyrics(music_list, output_file):
    """
    Get lyrics from a list of music using the DeepSeek API.
    """
    # Create a DeepSeek client
    client = OpenAI(api_key='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')

    response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are a music lover and you want to get the lyrics for a list of music."},
        {
            "role": "user",
            "content": f"Get the lyrics for the following music: {music_list}"
        }
    ],
    stream=False
    )

    print(response.choices[0].message.content)

# Load the music list from an Excel file
music_df = pd.read_excel("compiled_subtitles.xlsx")
for music in music_df.loc[147:,"legenda"]:
    get_lyrics(music, ".txt")
    time.sleep(1)