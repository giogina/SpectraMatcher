import numpy as np


def local_extrema(data):
    data = np.asarray(data)
    dx = np.diff(data)

    rising = dx > 0
    falling = dx < 0
    steady = dx == 0

    minima = np.where(falling[:-1] & rising[1:])[0]+1
    maxima = np.where(rising[:-1] & falling[1:])[0]+1

    overlap = 2
    while any(steady):
        new_minima = np.where(falling[:-overlap] & steady[1:-1] & rising[overlap:])[0] + int((overlap+1) / 2)
        new_maxima = np.where(rising[:-overlap] & steady[1:-1] & falling[overlap:])[0] + int((overlap+1) / 2)
        minima = np.concatenate((minima, new_minima))
        maxima = np.concatenate((maxima, new_maxima))
        overlap += 1
        steady = steady[1:] & steady[:-1]

    minima = np.sort(minima)
    maxima = np.sort(maxima)
    if len(maxima)>0:
        if len(minima)==0  or minima[0] > maxima[0]:
            minima = np.concatenate(([0], minima))
        if len(minima)==0 or minima[-1] < maxima[-1]:
            minima = np.concatenate((minima, [len(data)-1]))
    return minima, maxima

def find_peaks(data, prominence=None, width=None):
    try:
        data = np.asarray(data)
        minima, maxima = local_extrema(data)
        if len(minima) == 0:
            return [], {}

        properties = {}
        if len(minima) != len(maxima)+1:
            print("Find peaks: Something went wrong with the minima/maxima: ", minima, maxima)
            return [], {}
        m = np.stack((minima[:-1], maxima, minima[1:]), axis=1)
        s =  np.asarray(find_bases(data, minima, maxima))
        d = data[s]
        mask = (d[:, 0] < d[:, 1]) & (d[:, 1] > d[:, 2])   # should always be true; just to make sure.
        if prominence is not None:
            prominences = d[:, 1] - np.maximum(d[:, 0], d[:, 2])
            prominence_mask = prominences >= prominence
            mask = mask & prominence_mask
        if width is not None:
            try:
                left_pieces = [np.concatenate((data[l:p + 1][::-1] - data[p]/2, np.array([-0.1]))) for l, p in s[:, :2]]
                right_pieces = [np.concatenate((data[p:r + 1] - data[p]/2, np.array([-0.1]))) for p, r in s[:, 1:]]
                left_widths = np.asarray([[c + (p[c]/(p[c]-p[c+1]) if c+1<len(p) else 0) for c in [np.min(np.where(p<0)[0])-1]][0] for p in left_pieces])
                right_widths = np.asarray([[c + (p[c]/(p[c]-p[c+1]) if c+1<len(p) else 0) for c in [np.min(np.where(p<0)[0])-1]][0] for p in right_pieces])
                widths = left_widths+right_widths
                width_mask = widths >= width
                mask = mask & width_mask
                properties['widths'] = widths[mask]
            except Exception as e:
                print("Widths determination error: ", e)
                properties['widths'] = []
        if prominence is not None:
            properties['prominences'] = prominences[mask]
        return maxima[mask], properties
    except Exception as e:
        print("find_peak exception: ", e)
        return [], {}

def find_bases(data, minima, maxima):
    if len(maxima) == 0:
        return []
    max_values = data[maxima]
    max_index = maxima[np.argmax(max_values)]
    left_minima = minima[minima < max_index]
    right_minima = minima[minima > max_index]
    if len(left_minima) == 0 or len(right_minima) == 0:
        return []
    left_base_index = left_minima[np.argmin(data[left_minima])]
    right_base_index = right_minima[np.argmin(data[right_minima])]
    minmaxmin = [[left_base_index, max_index, right_base_index]]
    return find_bases(data, left_minima, maxima[maxima < max_index]) + minmaxmin + find_bases(data, right_minima, maxima[maxima>max_index])


