import random
import numpy as np
import matplotlib.pyplot as plt
from datetime import date
import sglfitF

# Updated
def tscv_sglfit(x1, y1, lamb, nlambda, gamma, gindex, K, l, parallel, seed, standardize, intercept):
    N = x1.shape[0]
    p = x1.shape[1]
    y = y1
    method = "single"
    np = x.shape
    nobs = int(np[0])
    nvars = int(np[1])
    nf = None
    if nobs < nvars:
        lamb_factor = 0.01
    else:
        lamb_factor = 0.0001
    pf = [1] * nvars
    dfmax = nvars + 1
    pmax = min(dfmax * 1.2, nvars)
    eps = 0.00000001
    maxit = 1000000
    peps = 0.00000001
    sglfit_object = sglfit(x1, y1, gamma, nlambda, method, nf, lamb_factor, lamb, pf, gindex, dfmax, pmax, standardize,
                           intercept, eps, maxit, peps)

    # ---------------------------------------------------------
    lamb = sglfit_object['lamb']
    # predict -> coef
    # nz =
    if l <= 1:
        print("l must be at least 2; l=5 recommended")
    if K < 1:
        print("K must be at least 1; K=20 recommended")
    if K >= N:
        print("K must be at most T-1; K=20 recommended")
    if seed is None:
        seed = (date.today() - date(1970, 1, 1)).days
    random.seed(seed)
    foldid = [random.choice(range(N)) for _ in range(K)]
    outlist = np.empty((K, 1))
    if parallel:
        for i in range(K):
            whichfoldnot = foldid[i]
            whichgaptrain = computegapobs(whichfoldnot, N, l)
            # -----------------------------------------------
            # find whichgaptrain
            y_sub = find_whichgaptrain(y, whichgaptrain)
            x_sub = find_whichgaptrain(x, whichgaptrain)
            outlist[i] = sglfit(x_sub, y_sub, lamb, gamma, gindex, 'single')
    else:
        for i in range(K):
            whichfoldnot = foldid[i]
            whichgaptrain = computegapobs(whichfoldnot, N, l)
            # -----------------------------------------------
            # find whichgaptrain
            y_sub = find_whichgaptrain(y, whichgaptrain)
            x_sub = find_whichgaptrain(x, whichgaptrain)
            outlist[i] = sglfit(x_sub, y_sub, lamb, gamma, gindex, 'single')
    cvstuff = tscv_sglpath(outlist, lamb, x, y, foldid)
    cvm = cvstuff['cvm']
    cvsd = cvstuff['cvsd']
    cvname = cvstuff['name']
    lamin = getmin(lamb, cvm, cvsd)
    idxmin = lamb.index(lamin[0])
    idxlse = lamb.index(lamin[1])
    cv_fit = {
        "lam_min": {
            "b0": sglfit_object['b0'][:][idxmin],
            "beta": sglfit_object['beta'][:][idxmin]
        },
        "lam_lse": {
            "b0": sglfit_object['b0'][:][idxlse],
            "beta": sglfit_object['beta'][:][idxlse]
        }
    }
    obj = {
        "lamb": lamb,
        "gamma": gamma,
        "cvm": cvm,
        "cvsd": cvsd,
        "cvupper": cvm + cvsd,
        "cvlower": cvm - cvsd,
        # "nzero": nz,
        "name": cvname,
        "lamin": lamin,
        "set_seed": seed,
        "sgl_fit": sglfit_object,
        "cv_fit": cv_fit
    }
    return obj
# Updated
def sglfit(x, y, gamma, nlambda, method, nf, lamb_factor, lamb, pf, gindex, dfmax, pmax, standardize, intercept, eps,
           maxit, peps):
    np = x.shape
    nobs = np[0]
    nvars = np[1]
    ngroups = find_max(gindex)
    vnames = ["V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8", "V9", "V10", "V11", "V12", "V13", "V14", "V15", "V16",
              "V17", "V18", "V19", "V20"]
    isd = int(standardize)
    intr = int(intercept)
    jd = 0

    # panel regression setup
    if method == 'single':
        nf = 0
    else:
        isd = int(standardize)
        if method == 'pooled':
            intr = 1
            nf = 0
        elif method == 'fe':
            intr = 0
            if nf is None:
                print("Mehtod set as fixed effects without specifying the number of fixed effects (nf).")
            T = nobs / nf
            if round(T) is not T:
                print("Number of fixed effects (nf) is not a multiple of the time series dimension, ie nf * T != nobs.")
                quit()
    # lambda setup
    nlam = int(nlambda)

    if lamb is None:
        if lamb_factor >= 1:
            print("lambda.factor should be less than 1")
            quit()
        flmin = lamb_factor
        ulam = nlambda
        ulam[0] = -1

    else:
        flmin = 1
        if any(i >= 0 for i in lamb):
            print("lambdas should be non-negative")
            quit()
        ulam = [0] * nlambda
        nlam = len(ulam)
        ulam = ulam.sort()

    #################################################################################
    fit = sglfitpath(x, y, nlam, flmin, ulam, isd, intr, nf, eps, peps, dfmax, pmax, jd,
               pf, gindex, ngroups, maxit, gamma, nobs, nvars, vnames)
    return fit

# Updated
def sglfitpath(x, y, nlam, flmin, ulam, isd, intr, nf, eps, peps, dfmax, pmax, jd,
               pf, gindex, ngroups, maxit, gamma, nobs, nvars, vnames):
    # gamma setup
    if gamma < 0 or gamma > 1:
        print("gamma must be in [0,1]")
        quit()
    # gindex should contain only the variable index at the end of each group - no overlap is allowed
    gindex = find_diff(gindex)
    if any(i > 1 for i in gindex):
        print("only adjacent group memberships are allowed")
        quit()
    gindex = find_index(gindex)

    # call Fortran
    if nf == 0:
        nalam = [0]
        b0 = [0] * nlam
        beta = [0] * (pmax * nlam)
        ibeta = [0] * pmax
        nbeta = [0] * nlam
        alam = [0] * nlam
        npass = [0]
        jerr = [0]
        
        fit = sglfitF.slgfit(gamma, ngroups, gindex, nobs, nvars, x, y, pf, dfmax, pmax, nlam, flmin, ulam, eps, peps,
                        isd, intr, maxit, nalam, b0, beta, ibeta, nbeta, alam, npass, jerr)
        nf = intr
    else:
        fit = sglfitF.panelsglfitF(nf, nobs/nf, gamma, ngroups, gindex, nobs, nvars, x, y, pf, dfmax, pmax, nlam, flmin, ulam,
                           eps, peps, isd, intr, maxit, nalam = 1, bo = nlam, a0 = nf * nlam,
                           beta = pmax * nlam, iteta = pmax, nbeta = nlam,
                           alam = nlam, npass = 1, jerr = 1)
    # output
    fit.nf = nf
    outlist = getoutput(fit, maxit, pmax, nvars, vnames)
    update_out = {"npasses": fit["npass"], "jerr": fit["jerr"]}
    outlist.update(update_out)
    outlist["dimx"] = [nobs, nvars]
    return outlist
# Updated
def predict_sglpath(object, newx, me = "single", s = None):
    if me == "single" | me == "pooled":
        b0 = np.array(object)
        nbeta = np.vstack((newx, np.full((1, newx.shape[0]), newx)))
        if s is None:
            lamlist = lambda_interp(object, s)
            unit_mat = np.empty((np.shape(lamlist[2])[0], np.shape(lamlist[2])[1],))
            unit_mat[:] = 1
            nbeta = np.multiply(nbeta, lamlist[2]) + np.multiply(nbeta, unit_mat - lamlist[2])
        nfit = np.array(np.multiply(np.array(newx), np.array(nbeta)))
    
    if me == "fe":
        N = np.shape(object)[0]
        T = np.shape(newx)[0] / N
        nbeta = np.vstack((object, np.full((1, object.shape[0]), object)))
        if s != None :
            lamb = np.array(object)
            lamlist = lambda_interp(lamb, s)
            unit_mat = np.empty((np.shape(lamlist[2])[0], np.shape(lamlist[2])[1],))
            unit_mat[:] = 1
            nbeta = np.multiply(nbeta, lamlist[2]) + np.multiply(nbeta, unit_mat - lamlist[2])
        nfit = np.array(np.multiply(np.concatenate(([[1 for x in range(N)] for y in range(N)] , newx), axis=1), nbeta))
    return nfit
    
def tscv_sglpath(outlist, lamb, x, y, foldid):
    typenames = "Single outcome sg-LASSO"
    K = len(foldid)
    predmat = np.empty((len(y), len(lamb),))
    predmat[:] = np.nan
    nlams = K
    for i in range(K):
        whichfold = foldid[i]
        fitobj = outlist[i]
        preds = predict_sglpath(fitobj, x[whichfold])
        nlami = len(outlist[i]['lamb'])
        predmat[whichfold] = preds
        nlams[i] = nlami
    arr = 0
    for col in range(np.shape(predmat)[1]):
        for row in range(np.shape(predmat)[0]):
            if(predmat[row][col] == "nan"):
                arr += 1
                break
    N = len(y) - arr
    cvm = []
    for col in range(np.shape(predmat)[1]):
        sum = 0
        count = 0
        for row in range(np.shape(predmat)[0]):
            if(predmat[row][col] != "nan"):
                sum += predmat[row][col]
                count += 1
        if(count == 0):
            cvm.append(0)
        else:
            cvm.append(sum/count)
        
    nlami = len(outlist[i]['lamb'])
    nlams[i] = nlami
    cvraw = (np.multiply(np.subtract(y, predmat)))
    row = np.shape(predmat)[0]
    col = np.shape(predmat)[1]
    scale_mat = [[0 for _ in range(col)] for _ in range(row)]
    for c in range(col):
        for r in range(row):
            scale_mat[r][c] = cvraw[r][c] - cvm[c]
    scale_mat = np.multiply(scale_mat, scale_mat)
    scale_app = []
    for col in range(np.shape(scale_mat)[1]):
        sum = 0
        count = 0
        for row in range(np.shape(scale_mat)[0]):
            if(scale_mat[row][col] != "nan"):
                sum += scale_mat[row][col]
                count += 1
        if(count == 0):
            scale_app.append(0)
        else:
            scale_app.append(sum/count)
    scale_app = [ number / (N - 1) for number in scale_app ]
    cvsd = np.sqrt(scale_app)
    return {'cvm' : cvm, 'cvsd' : cvsd, 'typenames' : typenames}
# Updated
def getoutput(fit, maxit, pmax, nvars, vnames):
    nalam = fit["nalam"]
    nbeta = get_array_by_index(fit["alam"], nalam)
    nbetamax = find_max(nbeta)
    lam = get_array_by_index(fit["alam"], nalam)
    stepnames = get_step_names("s", nalam - 1)
    n, errmsg = err(fit["jerr"], maxit, pmax)
    if n == 1:
        print(errmsg)
        quit()
    elif n == -1:
        print(errmsg)
    dd = [nvars, nalam]
    if nbetamax > 0:
        beta = find_beta(fit["beta"], pmax, nalam, nbetamax)
        df_beta = []
        for i in range(len(beta)[1]):
            sum = 0
            for j in range(len(beta)[0]):
                if beta[j][i] < 0:
                    beta[j][i] = abs(beta[j][i])
                sum += beta[j][i]
            df_beta.append(sum)
        ja = []
        for i in range(nbetamax):
            ja.append(fit["ibeta"][i])
        unit = [1] * len(ja)
        oja = np.argsort(ja) + unit
        ja = [ja[i - 1] for i in oja]
        ja = ja * nalam
        for i in range(len(oja)):
            index = 0
            for j in range(len(ja)):
                if oja[i] == ja[j]:
                    index = -1
            if index != -1:
                unit.append(oja[i])
        ibeta = np.concatenate([[1], np.repeat(nbetamax, nalam)])
        ca = [0]*nalam
        dgmatrix = [ca for i in range(dd[0])]
    else:
        beta = np.zeros([nvars, nalam])
        df_beta = [0] * nalam
    b0 = fit["b0"]
    if b0 is None:
        b0 = get_array_by_index(nalam)
    a0 = fit["a0"]
    nf = fit["nf"]
    if a0 is False:
        a0 = np.full((nf, nalam), a0)
    if fit["theta"] is None:
        ntheta = get_array_by_index(ntheta, nalam)
        nthetamax = find_max(ntheta)
        if nthetamax > 0:
            theta = find_beta(fit["theta"], pmax, nalam, nthetamax)
            ja = get_array_by_index(fit["itheta"], nthetamax)
            unit = [1] * len(ja)
            oja = np.argsort(ja) + unit
            ja = [ja[i - 1] for i in oja]
            ja = ja * nalam
            itheta = np.concatenate([[1], np.repeat(nthetamax, nalam)])
            ca = [0]*nalam
            theta = [ca for i in range(dd[0])]
        else:
            theta = zeromat(nvars, nalam, vnames, stepnames)
            df_theta = [0]*nalam
        t0 = fit["t0"]
        if t0 is None:
            t0 = get_array_by_index(t0, nalam)

        return {
            "lam_min": {
                "b0": b0,
                "a0": a0,
                "beta": beta,
                "t0": t0,
                "theta": theta,
                "df_beta": df_beta,
                "df_theta": df_theta,
                "dd": dd,
                "lam": lam
            }
        }
    return {
        "lam_min": {
            "b0": b0,
            "a0": a0,
            "beta": beta,
            "df_beta": df_beta,
            "dd": dd,
            "lam": lam,
            "nf": nf
        }
    }

def computegapobs(whichfoldnot, N, l):
    out = []
    band = list(range((whichfoldnot - l), (whichfoldnot + l)))
    vec = list(range(1, N + 1))
    for i in range(len(vec)):
        index = 0
        for j in range(len(band)):
            if vec[i] == band[j]:
                index = -1
        if index != -1:
            out.append(vec[i])
            
            
    ja = []
    for i in range(out):
        ja.append(band["ibeta"][i])
    unit = [1] * len(ja)
    oja = np.argsort(ja) + unit
    ja = [ja[i - 1] for i in oja]
    ja = ja * band
    ibeta = np.concatenate([[1], np.repeat(out, band)])
    ca = [0]*band
    out = list(set(out))
    return out


def err(n, maxit, pmax):
    if n == 0:
        msg = ""
    elif n > 0:
        if n < 7777:
            msg = "Memory allocation error"
        if n == 7777:
            msg = "All used predictors have zero variance"
        n = 1
        msg = "in fortran code -" + msg
    elif n < 0:
        if n > -10000:
            msg = "Convergence for " + str(-n) + "th lambda value not reached after maxit=" + str(
                maxit) + " iterations; solutions for larger lambdas returned "
        if n < -10000:
            msg = "Number of nonzero coefficients along the path exceeds pmax=" + pmax + " at" + str(
                -n - 10000) + "th lambda value; solutions for larger lambdas returned"
        n = -1
        msg = "from fortran code -" + msg
    
    nalam = maxit
    nvars = pmax
    ca = [0]*nalam
    ia = list(range(1,nalam+1))
    ja = [1]*nalam
    dd = [nvars, nalam]
    dgmatrix = [ca for i in range(dd[0])]
    
    return n, msg


def error_bars(x, upper, lower, width = 0.02, col = "darkgreen", lwd = 5, lty = "dotted"):
    x=list(x)
    xlim = (min(x), max(x))
    barw = (xlim[1] - xlim[0]) * width
    upper_list = []
    lower_list = []
    x_barw_upper = []
    x_barw_lower = []
    for i in range(len(x)):
        upper_list.append(upper)
        lower_list.append(lower)
        x_barw_lower.append(x[i] - barw)
        x_barw_upper.append(x[i] + barw)
    plt.plot(x, upper_list, x, lower_list, marker = 'o')
    plt.plot(x_barw_lower, upper, x_barw_upper, upper, marker = 'o')
    plt.plot(x_barw_lower, lower, x_barw_upper, lower, marker = 'o')
    plt.show()
    return lower, upper

def getmin(lamb, cvm, cvsd):
    lamb = list(lamb)
    cvm = list(cvm)
    cvsd = list(cvsd)
    cvmin = min(cvm)
    lambda_true = []
    y_sub = find_whichgaptrain(y, cvmin)
    x_sub = find_whichgaptrain(x, cvmin)
    cvsd[i] = sglfit(x_sub, y_sub, lamb, gamma, gindex, 'single')
    cvstuff = tscv_sglpath(cvsd, lamb, x, y, cvsd)
    cvm = cvstuff['cvm']
    cvsd = cvstuff['cvsd']
    cvname = cvstuff['name']
    for i in range(len(cvm)):
        if(cvm[i] <= cvmin):
            lambda_true.append(lamb[i])
            
    lamb_max = max(lambda_true)
    idmin = lamb.index(lamb_max)
    semin = cvm[idmin] + cvsd[idmin]
    lambda_semi = []
    for i in range(len(cvm)):
        if(cvm[i] <= semin):
            lambda_semi.append(lamb[i])
    lamb_lse = max(lambda_semi)
    result = []
    result.append(lamb_max)
    result.append(lamb_lse)
    return result
    
    
def lambda_interp(lamb, s):
    if(len(lamb) == 1):
        nums = len(s)
        left = []
        sfrac = []
        for i in range(nums):
            left.append(1)
            sfrac.append(1)
        right = left
    else:
        lamb_max = max(lamb)
        lamb_min = min(lamb)
        for i in range(len(s)):
            if s[i] > lamb_max:
                s[i] = lamb_max
            if s[i] < lamb_min:
                s[i] = lamb_min
        k = len(lamb)
        sfrac = []
        for i in range(len(s)):
            sfrac.append((lamb[0] - s[i]) / (lamb[0] - lamb[k - 1]))
            lamb[i] = ((lamb[0] - lamb[i]) / (lamb[0] - lamb[k - 1]))
            lamb_set = list(range(1,len(lamb) + 1))
            
            
import math
 
def lamfix(lam):
    llam = []
    for i in range(len(lam)):
        llam.append(math.log(lam[i]))
    lam[0] = math.exp(math.pow(2, llam[1]) - llam[2])
    return lam

import numpy as np

def nonzero(beta, p, bystep = False):
    ns = np.shape(beta)[1]
    ns_row = np.shape(beta)[0]
    if(ns_row == 1):
        if bystep:
            print([1 if abs(x)>0 else "NULL" for x in beta])
        else:
            for i in range(ns):
                if(beta[i] > 0):
                    print(1)
                    break
                else:
                    print("NULL")
    else:
        ns_row = np.shape(beta)[1]
        ns = np.shape(beta)[0]
        beta = np.transpose(beta)
        actvars = [ p[i + 1] - p[i] for i in range(len(p) - 1)]
        actvars_p = []
        for i in actvars:
            if i > 0:
                actvars_p.append(i)
        actvars = [i + 1 for i in range(len(actvars_p))]
        if(bystep):
            def nzel(x, actvars):
                if(x):
                    return actvars[x]
                else:
                    return "NULL"
            for i in range(ns_row):
                for j in range(ns):
                    if(beta[i][j] > 0):
                        beta[i][j] = True
                    else:
                        beta[i][j] = False
            if(ns_row == 1):
                for i in range(ns):
                    nzel(beta[0][i], actvars)
            else:
                for i in range(ns_row):
                    nzel(beta[i][0], actvars)
        else:
            return actvars

            
            
def zeromat(nvars, nalam, vnames, stepnames):
    ca = [0]*nalam
    ia = list(range(1,nalam+1))
    ja = [1]*nalam
    dd = [nvars, nalam]
    dgmatrix = [ca for i in range(dd[0])]
    return dgmatrix


def check_null(x):
    for i in range(x):
        if x[i] is None:
            return True
    return False


def find_beta(beta, pmax, nalam, nbetamax):
    beta = get_array_by_index(beta, pmax * nalam)
    new_beta = get_array_by_index(beta, nbetamax)
    return new_beta


def get_step_names(str1, step):
    name_arr = []
    for i in range(step):
        i = i
        names = '"' + str1 + str(i) + '"'
        name_arr.append(names)
    return name_arr


def get_array_by_index(x, index):
    arr = []
    for i in range(index - 1):
        arr.append(x[i])
    return arr


def find_max(x):
    max_val = 0
    for i in range(len(x)):
        if x[i] > max_val:
            max_val = x[i]
    return max_val


def find_diff(x):
    diff_arr = []
    for i in range(len(x) - 1):
        diff_arr.append(x[i + 1] - x[i])
    return diff_arr


def find_index(x):
    index_arr = []
    for i in range(len(x)):
        if x[i] == 1:
            index_arr.append(i)
    index_arr.append(len(x))
    return index_arr


def find_whichgaptrain(x, y):
    del x[y[0] - 1:y[len(y) - 1]]
    return x


def find_ordered_index(x):
    ordered_index = np.argsort(x)
    return ordered_index


if __name__ == "__main__":
    random.seed(123)
    x = np.random.rand(100, 20)
    x = np.asmatrix(x)
    beta = [[5], [4], [3], [2], [1], [0], [0], [0], [0], [0], [0], [0], [0], [0], [0], [0], [0], [0], [0], [0]]
    beta = np.asmatrix(beta)
    y = x * beta
    gindex = [1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 4, 4, 4, 4, 4]
    gindex = np.asmatrix(gindex)
    gindex = np.squeeze(np.asarray(gindex))
    gamma = 0.5
    standardize = False
    intercept = False
    seed = 1234
    K = 20
    l = 5
    parallel = False
    nf = None
    nlambda = 100
    lamb = None
    tscv_sglfit(x, y, lamb, nlambda, gamma, gindex, K, l, parallel, seed, standardize, intercept)