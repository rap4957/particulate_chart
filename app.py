import panel as pn
import json
import numpy as np
import pandas as pd
import seaborn as sns
import requests
from matplotlib import pyplot as plt
pn.extension()

#Declare global variables

df_store = {"df": None, "df_filtered": None } 
GITHUB_USER = "rap4957"
GITHUB_REPO = "particulate_chart"
GITHUB_BRANCH = "main"  # or "master" or whichever branch you use
# 1. Collect files
# Get list of files from the GitHub repo



    
def get_github_json_files():
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/data"
    try:
        response = requests.get(url)
        files = response.json()
        if isinstance(files, list):
            return [f["name"] for f in files if f["name"].endswith(".json")]
                    # Make sure the response is a list
        else:
            print("GitHub API error:", files)
            return []
    except Exception as e:
        print("Error fetching files:", e)
        return []
                       




# 2. Widgets
files_widget = pn.widgets.Select(name="Pick a JSON file", options=[])
rpt_selector = pn.widgets.MultiSelect(name="Select Reports to Plot", options=[], size=6)
sample_selector = pn.widgets.MultiSelect(name="Select Samples to Plot", options=[], size=6)
plt_bins = pn.widgets.CheckBoxGroup(
    name='Size Bins', value=['10um', '25um', '50um'], options=['10um', '25um', '50um'],
    inline=True)
df_widget = pn.widgets.DataFrame(df_store['df'], sizing_mode='stretch_width')

# 3. Output panes
output_json = pn.pane.JSON({}, depth=2)
output_plot = pn.pane.Matplotlib(height=500, width=500, tight=True)
max_particle_plot = pn.pane.Matplotlib(height=500, width=500, tight=True)

def update_file_options(event=None):
    files_widget.options = get_github_json_files()

update_file_options()

# 4. Callback
def read_JSON(event):
    print('reading new JSON and initializing df as None')
    file_name = event.new
    if file_name:
        raw_url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/refs/heads/{GITHUB_BRANCH}/data/{file_name}"
        print(f'Reading URL {raw_url}')
        response = requests.get(raw_url)
        if response.status_code == 200:
            data = json.loads(response.text)
            output_json.object = data  # update pane content
            df_store['df'] = parse_JSON(data)

    else:
        output_json.object = {"Error": f"Failed to load {file_name}"}

def parse_JSON(data):
    df_data = []
    for report in data:
        #report['Date'] = eval(report['Date']) #JSON doesn't recognize python code so unwrap the dt.DateTime type date from the string stored in this field
        #print(f"Report: {report['Report No.']}")
        for sample in report['Samples']:
            #look through the counts for each sample
            #the 'counts' field is either a dict (if only one replicate) or a list of dicts (in the case of multiple replicates) so check which one it is 
            bin_10um = 0
            bin_25um = 0
            bin_50um = 0

            if(type(sample['Counts'])==dict):
                #if its a dict there is only one replicate
                bin_10um = sample['Counts']['10um']/sample['Volume Tested per Replicate (mL)']
                bin_25um = sample['Counts']['25um']/sample['Volume Tested per Replicate (mL)']
                bin_50um = sample['Counts']['50um']/sample['Volume Tested per Replicate (mL)']
            else:
                for count in sample['Counts']:
                    bin_10um += count['10um']/sample['Volume Tested per Replicate (mL)']
                    bin_25um += count['25um']/sample['Volume Tested per Replicate (mL)']
                    bin_50um += count['50um']/sample['Volume Tested per Replicate (mL)']
            bin_10um = bin_10um/sample['Num Replicates'] #average the replicates
            bin_25um = bin_25um/sample['Num Replicates'] #average the replicates
            bin_50um = bin_50um/sample['Num Replicates'] #average the replicates
            #print(f"Sample max particle size {sample['Max Particle Size (um)']}")
            #print(f"Sample: {sample['Name']} \n10um (#/25mL):{bin_10um*25} \n25um (#/25mL):{bin_25um*25} \n50um (#/25mL):{bin_50um*25}")
            for i, count, bin_size in zip(range(3), 
                                          [bin_10um*25, bin_25um*25, bin_50um*25], 
                                          ['10um','25um','50um']):
                df_data.append({'Report': report['Report No.'],
                                'Date': report['Date'],
                                'Sample': sample['Name'],
                                'Bin': bin_size,
                                'Max Particle Size (um)': sample['Max Particle Size (um)'],
                                'Count': count,
                               'Notes': report['Notes']})
                
    df = pd.DataFrame(df_data)
    rpt_selector.options = list(df['Report'].unique())
    return df
            
def update_plot(event):
    df = df_store['df']
    if df is None:
        return 
    sample_selector.options = list(df[df['Report'].isin(rpt_selector.value)]['Sample'].unique())
    if df is not None and event.new:
        selected = event.new
        #print(event.new)
        tmp = df[(df['Report'].isin(rpt_selector.value)) & 
                 (df['Sample'].isin(sample_selector.value)) & 
                 (df['Bin'].isin(plt_bins.value))
                ]
        tmp_widget = df[df['Report'].isin(rpt_selector.value) & df['Sample'].isin(sample_selector.value)]
        if(len(tmp)>0):
            indices = tmp.index
            ax = sns.barplot(x='Bin', y='Count', hue='Sample', data=tmp)
            #ax = df[selected].plot(kind="bar", figsize=(6,4))
            ax.set_title("Particle Counts")
            output_plot.object = ax.figure
            plt.close(ax.figure)
            ax = sns.barplot(y='Sample', x='Max Particle Size (um)', data=tmp.sort_values(by='Max Particle Size (um)', ascending=False))
            max_particle_plot.object = ax.figure
            plt.close(ax.figure)
            df_widget.value = tmp_widget[['Report', 'Sample', 'Bin', 'Count', 
                                          'Max Particle Size (um)', 'Notes']].reset_index(drop=True)
            
# 5. Link callback
files_widget.param.watch(read_JSON, 'value')
rpt_selector.param.watch(update_plot, 'value')
sample_selector.param.watch(update_plot, 'value')
plt_bins.param.watch(update_plot, 'value')

# 6. Layout
app = pn.Column(
    pn.Row(
        pn.Column("## Particulate File Picker", files_widget, rpt_selector, sample_selector, plt_bins,sizing_mode="stretch_both"),
        pn.Column(pn.Row("##Charts", output_plot, max_particle_plot, sizing_mode="stretch_both"))),
    pn.Row(df_widget),
    sizing_mode="stretch_both")

app.servable()
