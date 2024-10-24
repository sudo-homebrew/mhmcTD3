#!/usr/bin/env python

from .settings import ENABLE_VISUAL

if ENABLE_VISUAL:
    from PyQt6 import QtWidgets, QtCore, QtGui
    from PyQt6.QtCore import Qt
    import pyqtgraph as pg
    import numpy as np
    import time
    QtCore.QLoggingCategory.setFilterRules("*.debug=false\nqt.core.plugin.factoryloader.warning=false")

    pg.setConfigOptions(antialias=False)

    class DrlVisual(pg.GraphicsLayoutWidget):
        def __init__(self, state_size, hidden_size):
            super().__init__(None)
            self.show()
            self.resize(1980, 1200)

            self.scroll = QtWidgets.QScrollArea()
            self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)

            self.state_size = state_size
            self.hidden_sizes = [hidden_size, int(hidden_size * 2), int(hidden_size * 2), hidden_size, hidden_size // 2, hidden_size // 2 ** 2,
                                hidden_size // 2 ** 3]

            self.mainLayout = QtWidgets.QVBoxLayout()
            self.setLayout(self.mainLayout)

            # States
            self.plot_item_states = self.addPlot(title="States", colspan=3)
            self.plot_item_states.setXRange(-1, self.state_size, padding=0)
            self.plot_item_states.setYRange(-1, 1, padding=0)

            self.bar_graph_states = pg.BarGraphItem(x=range(self.state_size), height=np.zeros(self.state_size), width=1)
            self.plot_item_states.addItem(self.bar_graph_states)

            self.hidden_plot_items = []
            self.hidden_bar_graphs = []
            self.hidden_line_plots = []
            i = 0

            for hidden_size in self.hidden_sizes:
                self.nextRow()
                titles = ['Hidden Layer 1', 'Hidden Layer 2', 'Hidden Layer 3', 'Hidden Layer 4', 'Hidden Layer 5', 'Hidden Layer 6', 'Hidden Layer 7']
                # plot_item = self.addPlot(title=f"Hidden layer {i}", colspan=3)
                plot_item = self.addPlot(title=titles[i], colspan=3)
                plot_item.setXRange(-1, hidden_size, padding=0)
                plot_item.setYRange(-0.5, 2.3, padding=0)

                bar_graph = pg.BarGraphItem(x=range(hidden_size), height=np.zeros(hidden_size), width=0.8)
                plot_item.addItem(bar_graph)

                line_plot = plot_item.plot(x=range(hidden_size), brush='r', symbol='x', symbolPen='r')
                line_plot.setPen(None)
                line_plot.setSymbolSize(5)

                self.hidden_bar_graphs.append(bar_graph)
                self.hidden_plot_items.append(plot_item)
                self.hidden_line_plots.append(line_plot)
                i += 1

            # Output layers
            self.nextRow()
            self.plot_item_action_linear = self.addPlot(title="Action Linear")
            self.plot_item_action_linear.setXRange(-1, 1, padding=0)
            self.plot_item_action_linear.setYRange(-1, 1, padding=0)
            self.bar_graph_action_linear = pg.BarGraphItem(x=range(1), height=np.zeros([0]), width=0.5)
            self.plot_item_action_linear.addItem(self.bar_graph_action_linear)

            self.plot_item_action_angular = self.addPlot(title="Action Angular")
            self.plot_item_action_angular.setXRange(-1, 1, padding=0)
            self.plot_item_action_angular.setYRange(-2.8, 2.8, padding=0)
            self.bar_graph_action_angular = pg.BarGraphItem(x=range(1), height=np.zeros([0]), width=0.5)
            self.plot_item_action_angular.addItem(self.bar_graph_action_angular)

            # transform = QtGui.QTransform()
            # transform.rotate(90)
            # self.plot_item_action_angular.getViewBox().setTransform(transform)

            self.plot_item_reward = self.addPlot(title="Accumulated Reward")
            self.plot_item_reward.setXRange(-1, 1, padding=0)
            self.plot_item_reward.setYRange(-3000, 5000, padding=0)
            self.bar_graph_reward = pg.BarGraphItem(x=range(1), height=np.zeros([0]), width=0.5)
            self.plot_item_reward.addItem(self.bar_graph_reward)

            self.iteration = 0

        def prepare_data(self, tensor):
            return tensor.squeeze().flip(0).detach().cpu()

        def update_layers(self, states, actions, hidden, biases):
            self.bar_graph_states.setOpts(height=self.prepare_data(states))
            actions = actions.detach().cpu().numpy().tolist()
            self.bar_graph_action_linear.setOpts(height=[actions[0]])
            self.bar_graph_action_angular.setOpts(height=[actions[1]])
            for i in range(len(hidden)):
                self.hidden_bar_graphs[i].setOpts(height=self.prepare_data(hidden[i]))
            pg.QtGui.QGuiApplication.processEvents()
            if self.iteration % 100 == 0:
                self.update_bias(biases)
            self.iteration += 1

        def update_bias(self, biases):
            for i in range(len(biases)):
                self.hidden_line_plots[i].setData(y=self.prepare_data(biases[i]))

        def update_reward(self, acc_reward):
            self.bar_graph_reward.setOpts(height=[acc_reward])
            if acc_reward > 0:
                self.bar_graph_reward.setOpts(brush='g')
            else:
                self.bar_graph_reward.setOpts(brush='r')


    def test():
        win = DrlVisual(30, 512)
        i = 200
        while (i):
            starttime = time.perf_counter()
            vals1 = np.random.rand(30)
            vals2 = np.random.rand(2)
            vals3 = [np.random.rand(512)] * 2
            vals4 = [np.random.rand(512)] * 2
            win.update_layers(vals1, vals2, vals3, vals4)
            win.update_reward(i * 10 * vals1[0])
            print(f"time: {time.perf_counter() - starttime}")
            i -= 1

    if __name__ == "__main__":
        test()
