def label_panel(ax, ord, lower=False, left=1):
    lb = ax.set_title('ABCDEFGH'[ord], loc='left', y=1, va='top' if lower else 'baseline', fontsize=12, fontweight='bold', ha='left')
    bb_plotonly = ax.get_window_extent()
    bb_withdeco = ax.get_tightbbox()
    x = left*(bb_withdeco.xmin - bb_plotonly.xmin) / bb_plotonly.bounds[2]
    lb.set_position((x, 1))
    return lb