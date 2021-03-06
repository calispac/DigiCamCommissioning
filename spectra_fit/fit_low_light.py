import numpy as np
from scipy.optimize import curve_fit
import peakutils
import utils.pdf

__all__ = ["p0_func", "slice_func", "bounds_func", "fit_func"]


# noinspection PyUnusedLocal,PyUnusedLocal
def p0_func(y, x, *args, config=None, **kwargs):
    """
    find the parameters to start a mpe fit with low light
    :param y: the Histogram values
    :param x: the Histogram bins
    :param args: potential unused positionnal arguments
    :param config: should be the fit result of a previous fit
    :param kwargs: potential unused keyword arguments
    :return: starting points for []
    """
    if type(config).__name__=='NoneType':
        mu = mu_xt = gain = baseline = sigma_e = sigma_1 = amplitude = offset = np.nan
        param = [mu, mu_xt, gain, baseline, sigma_e, sigma_1, amplitude, offset]
    else:
        mu = 0.001
        mu_xt = 0.08 #config[1, 0]
        gain = config[1, 0]
        baseline = config[0, 0]
        sigma_e = config[2, 0]
        sigma_1 = config[3,0]
        amplitude = np.nan
        offset = 0.
        #variance = config[8, 0]
        param = [mu, mu_xt, gain, baseline, sigma_e, sigma_1, amplitude, offset]


    if np.isnan(config[1, 0]):
        #print('mu is nan')
        return param


    max_bin = np.where(y != 0)[0][0]
    if x[max_bin]== 4095: max_bin-=1
    slice = [np.where(y != 0)[0][0], np.where(y != 0)[0][-1], 1]
    param[0] = np.average(x[slice[0]:slice[1]:slice[2]], weights=y[slice[0]:slice[1]:slice[2]])
    # Get a primary amplitude to consider
    param[6] = np.sum(y)

#    param[8] = np.sqrt(np.average((x - np.average(x, weights=y))**2, weights=y))
    if type(config).__name__ == 'NoneType':
        # Get the list of peaks in the Histogram
        threshold = 0.05
        min_dist = param[2] // 2

        peak_index = peakutils.indexes(y, threshold, min_dist)

        if len(peak_index) == 0:
            return param

        else:

            photo_peak = np.arange(0, peak_index.shape[-1], 1)
            param[2] = np.polynomial.polynomial.polyfit(photo_peak, x[peak_index], deg=1)[1]

            sigma = np.zeros(peak_index.shape[-1])
            for i in range(sigma.shape[-1]):

                start = max(int(peak_index[i] - param[2] // 2), 0)
                end = min(int(peak_index[i] + param[2] // 2), len(x))

                # if i == 0:

                #    param[0] = - np.log(np.sum(y[start:end]) / param[6])

                try:

                    temp = np.average(x[start:end], weights=y[start:end])
                    sigma[i] = np.sqrt(np.average((x[start:end] - temp) ** 2, weights=y[start:end]))

                except Exception as inst:
                    print('Could not compute weights for sigma !!!')
                    sigma[i] = param[4]

            sigma_n = lambda sigma_1, n: np.sqrt(param[4] ** 2 + n * sigma_1 ** 2)
            sigma, sigma_error = curve_fit(sigma_n, photo_peak, sigma, bounds=[0., np.inf])
            param[5] = sigma / param[2]

    param[0] = (param[0]-param[3])/param[2]
    if not( param[0]<np.inf): param[0]=100.
    if param[0]<0.: param[0]=0.01
    if not(param[2])<np.inf : param[2]=1.
    #print(param[0])
    return param



# noinspection PyUnusedLocal,PyUnusedLocal,PyUnusedLocal
def slice_func(y, x, *args, **kwargs):
    """
    returns the slice to take into account in the fit (essentially non 0 bins here)
    :param y: the Histogram values
    :param x: the Histogram bins
    :param args:
    :param kwargs:
    :return: the index to slice the Histogram
    """
    # Check that the Histogram has none empty values
    if np.where(y != 0)[0].shape[0] == 0:
        return []
    max_bin = np.where(y != 0)[0][0]
    if x[max_bin]== 4095: max_bin-=1
    return [np.where(y != 0)[0][0], np.where(y != 0)[0][-1], 1]


# noinspection PyUnusedLocal,PyUnusedLocal
def bounds_func(*args, config=None, **kwargs):
    """
    return the boundaries for the parameters (essentially none for a gaussian)
    :param args:
    :param kwargs:
    :return:
    """


    if True:

        param_min = [1.e-3, 1.e-4, 0., -np.inf, 0., 0., 0.,-np.inf]
        param_max = [2000., 1, np.inf, np.inf, np.inf, np.inf, np.inf,np.inf]


    else:

        mu = config[0]
        mu_xt = config[1]
        gain = config[2]
        baseline = config[3]
        sigma_e = config[4]
        sigma_1 = config[5]
        amplitude = config[6]
        offset = config[7]

        param_min = [0.    , 0., 0                   , -np.inf                  , 0.                       , 0.     ,0.    ,-np.inf]
        param_max = [np.inf, 1 , gain[0] + 10*gain[1], baseline[0]+5*baseline[1], sigma_e[0] + 5*sigma_e[1], np.inf ,np.inf, np.inf]

    return param_min, param_max


def fit_func(p, x, *args, **kwargs):
    """
    Simple gaussian pdf
    :param p: [norm,mean,sigma]
    :param x: x
    :return: G(x)
    """
    #mu, mu_xt, gain, baseline, sigma_e, sigma_1, amplitude, offset, variance = p
    mu, mu_xt, gain, baseline, sigma_e, sigma_1, amplitude, offset = p
    temp = np.zeros(x.shape)
    n_peak=10
    n_peakmin = 0
    if len(x)>0:
        n_peak = int(float(x[-1] - baseline) / gain * 1.5)
        n_peakmin = int(float(x[0] - baseline) / gain * 0.7)

    x = x - baseline
    for n in range(n_peakmin,n_peak):
        sigma_n = np.sqrt(sigma_e ** 2 + n * sigma_1 ** 2) # * gain
        temp += utils.pdf.generalized_poisson(n, mu, mu_xt) * utils.pdf.gaussian(x , sigma_n, n * gain)
        #temp += utils.pdf.generalized_poisson(n, mu, mu_xt) * utils.pdf.gaussian(x, sigma_n, n * gain + (offset if n!=0 else 0))

    return temp * amplitude

if __name__ == '__main__':

    print('Hello')