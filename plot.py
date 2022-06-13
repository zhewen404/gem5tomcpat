
import plotly.graph_objects as go
import argparse

def construct_argparser():
    parser = argparse.ArgumentParser(description='writeStats')
    parser.add_argument('-f',
                        '--file',
                        help='file to parse results',
                        default='out/base_canneal_simsmall_64_0_arr.txt'
                        )
    return parser

def plot(x, y):
    fig = go.Figure()
    for i in range(len(y)):
        base = 0
        for j in range(len(y[0])):
            fig.add_trace(
                go.Bar(
                    name='hit',
                    x=x[i],
                    y=y[i][j], 
                    offsetgroup=0,base=base,
                    marker_pattern_shape="",
                    marker=dict(color="green", line_color="green", pattern_fillmode="overlay")
                ), 
            )
            base += y[i][j]

if __name__ == '__main__':
    argparser = construct_argparser()
    args = argparser.parse_args()

    n = 0
    x_arr = []
    y_arr = []
    with open(args.file, 'r') as searchfile:
        for line in searchfile:
            if n == 0: 
                x_arr = line.split(',')
                x_arr = [i.replace('\n','') for i in x_arr]
            else: 
                arr = line.split(',')
                arr = [float(i.replace('\n','').replace('[', '').replace(']','')) for i in arr]
                y_arr.append(arr)
            n += 1
    print(x_arr)
    print(y_arr)

    fig = go.Figure()

    items = ['core_control', 'l1i', 'l1d', 'l2', 'l3', 'noc_control', 'noc_buffer']
    base = [0]*len(items)
    for i in range(len(items)):
        y_plot = [y_group[i] for y_group in y_arr]
        y_text = [f'{(y_group[i]/sum(y_group)*100):.2f}%' for y_group in y_arr]
        fig.add_trace(
            go.Bar(
                name=items[i],
                x=x_arr,
                y=y_plot, 
                offsetgroup=0, base=base,
                text=y_text
                # marker_pattern_shape="",
                # marker=dict(color="green", line_color="green", pattern_fillmode="overlay")
            ), 
        )
        base = [base_item+y_plot_item for base_item,y_plot_item in zip(base, y_plot)]

    fig.update_traces(textposition='inside')
    fig.show()  