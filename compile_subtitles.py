# script para ler todos os arquivos txt e compilar em um único
# deve ser gerado um arquivo excel com o nome do arquivo txt e o conteúdo

import os
import pandas

def compile_subtitles(directory, output_file):
    """
    Compile subtitles from all text files in a directory into a single Excel file.
    """
    # Get all text files in the directory
    files = [f for f in os.listdir(directory) if f.endswith('.txt')]
    
    # Create a Pandas DataFrame to store the subtitles
    df = pandas.DataFrame(columns=['File Name', 'Content'])
    
    # Iterate through each text file
    for file in files:
        with open(os.path.join(directory, file), 'r', encoding='utf-8') as f:
            content = f.read()
            print(os.path.splitext(os.path.basename(file))[0])
            df = df._append({'File Name': os.path.splitext(os.path.basename(file))[0], 'Content': content}, ignore_index=True)
    
    # Save the compiled subtitles to an Excel file
    df.to_excel(output_file, index=False)
    print(f"Compiled subtitles saved to {output_file}")

compile_subtitles(r'c:\Users\titoc\OneDrive\Documentos\hermessf\hermessf', 'compiled_subtitles.xlsx')