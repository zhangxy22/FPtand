import tensorflow.compat.v1 as tf
tf.disable_v2_behavior()
import numpy as np
from sklearn.model_selection import train_test_split
import pandas as pd
from scipy.stats import pearsonr
from matplotlib import ticker, gridspec


FP_length = 1024
batch_size = 32
Max_len = 1500
bit_size1 = 1024
bit_size = 2048
embedding_size = 100
emb = tf.Variable(tf.random.uniform([bit_size1 + 1, embedding_size], -1, 1), dtype=tf.float32)
pads = tf.constant([[1, 0], [0, 0]])
embeddings = tf.pad(emb, pads)

dataxa_train = pd.read_csv('CDK_train_a.csv')
dataxd_train = pd.read_csv('CDK_train_d.csv')
datay = pd.read_csv('y_train.csv')
datay_train = datay[['PCE']]

dataxa_test = pd.read_csv('CDK_test_a.csv')
dataxd_test = pd.read_csv('CDK_test_d.csv')
datayy = pd.read_csv('y_test.csv')
datay_test = datayy[['PCE']]

data_train_x = np.hstack((dataxd_train,dataxa_train))
data_train_y = datay_train

data_test_x = np.hstack((dataxd_test,dataxa_test))
data_test_y = datay_test



train_x = []
for i in range(len(data_train_x)):
    fp = [0] * Max_len
    n_ones = 0
    for j in range(bit_size):
        if j < 1024:
            if data_train_x[i][j] == 1:
                fp[n_ones] = j + 1
                n_ones += 1
        else:
            if data_train_x[i][j] == 1:
                fp[n_ones] = j + 1 - 1024
                n_ones += 1
    train_x.append(fp)
train_x = np.array(train_x, dtype=np.int32)
train_y = np.array(data_train_y , dtype=np.float32)

test_x = []
for i in range(len(data_test_x)):
    fp = [0] * Max_len
    n_ones = 0
    for j in range(bit_size):
        if j < 1024:
            if data_test_x[i][j] == 1:
                fp[n_ones] = j + 1
                n_ones += 1
        else:
            if data_test_x[i][j] == 1:
                fp[n_ones] = j + 1 - 1024
                n_ones += 1
    test_x.append(fp)
test_x = np.array(test_x, dtype=np.int32)
test_y = np.array(data_test_y , dtype=np.float32)


train_x_concat, test_x_concat, train_y_concat, test_y_concat, valid_x_concat, valid_y_concat = [], [], [], [], [], []

train_x, valid_x, train_y, valid_y = train_test_split(train_x, train_y, test_size=0.1,random_state=1)
print(train_x.shape, train_y.shape)
print(test_x.shape, test_y.shape)
print(valid_x.shape, valid_y.shape)

train_size = len(train_x)
test_size = len(test_x)
valid_size = len(valid_x)


from pylab import*
mpl.rcParams['font.sans-serif']=['SimHei']


def plot_scatter(x_train, y_train, x_test, y_test):
    # general plot options
    fig = plt.figure()
    gs = gridspec.GridSpec(1, 1)
    r, _ = pearsonr(x_test, y_test)
    # rho, _ = spearmanr(x, y)
    ma = np.max([x_train.max(), x_test.max(), y_train.max(), y_test.max()]) + 1
    ax = plt.subplot(gs[0])
    ax.scatter(x_train, y_train, s=20, color='b', alpha=0.3)
    ax.scatter(x_test, y_test, s=20, color='r', alpha=0.4)
    ax.tick_params(axis='both', which='major', direction='in', labelsize=18, pad=10, length=5)
    ax.set_xlabel(u"PCE(Experimental)/%", size=18, labelpad=10)
    ax.set_ylabel(u"PCE(Predictive)/%", size=18, labelpad=10)
    ax.legend(['train', 'test'], fontsize=13, loc='upper left')
    # ax.set_xlabel(u"PCE / %", size=24, labelpad=10)
    # ax.set_ylabel(u'PCE$^{%s}$ / %s' %(SVR,"%"), size=24, labelpad=10)
    ax.set_xlim(0, ma)
    ax.set_ylim(0, ma)
    ax.set_aspect('equal')
    ax.plot(np.arange(0, ma + 0.1, 0.1), np.arange(0, ma + 0.1, 0.1), color="k", ls="--")
    ax.annotate(u'$r$ = %.2f' % r, xy=(0.15, 0.85), xytext=(0.7, 0.1), xycoords='axes fraction', size=13)
    # extra options in common for all plot types
    xtickmaj = ticker.MaxNLocator(5)
    xtickmin = ticker.AutoMinorLocator(5)
    ytickmaj = ticker.MaxNLocator(5)
    ytickmin = ticker.AutoMinorLocator(5)
    ax.xaxis.set_major_locator(xtickmaj)
    ax.xaxis.set_minor_locator(xtickmin)
    ax.yaxis.set_major_locator(ytickmaj)
    ax.yaxis.set_minor_locator(ytickmin)
    ax.xaxis.set_ticks_position('both')
    ax.yaxis.set_ticks_position('both')
    ax.tick_params(axis='both', which='minor', direction='in', labelsize=22, pad=10, length=2)
    return


##################################################################
# ===================== model construction =======================
##################################################################

def init_weights(shape):
    return tf.Variable(tf.random_normal(shape, stddev=0.01))


def bias_variable(shape):
    return tf.Variable(tf.constant(0.01, shape=shape))


p_keep_conv = tf.placeholder(dtype=tf.float32)


class model():
    def __init__(self, embedding_size, p_keep_conv, Max_len):
        self.Max_len = Max_len
        self.nhid = 32
        self.kernel_size = [9]
        self.w2 = init_weights([self.kernel_size[0], embedding_size, 1, self.nhid])  # 64
        self.w_o = init_weights([self.nhid, 1])

        self.b2 = bias_variable([1, self.nhid])
        self.b_o = bias_variable([1])
        self.p_keep_conv = p_keep_conv

    def conv_model(self, X):
        l2 = tf.nn.relu(tf.nn.conv2d(X, self.w2, strides=[1, 1, 1, 1], padding='VALID') + self.b2)
        l2 = tf.squeeze(l2, [2])
        l2 = tf.nn.pool(l2, window_shape=[self.Max_len - self.kernel_size[0] + 1], strides=[3], pooling_type='MAX',
                        padding='VALID')  # stride =3
        l2 = tf.nn.dropout(l2, self.p_keep_conv)

        lout = tf.reshape(l2, [-1, self.w_o.get_shape().as_list()[0]])
        return lout


# ============================================================= #
X = tf.placeholder(tf.int32, [None, Max_len])
Y = tf.placeholder(tf.float32, [None, 1])
X_em = tf.nn.embedding_lookup(embeddings, X)
X_em = tf.reshape(X_em, [-1, Max_len, embedding_size, 1])

model = model(embedding_size, p_keep_conv, Max_len)
py_x = model.conv_model(X_em)

# ============================================================= #
temp_hid = 32
w1 = init_weights([temp_hid, 1])
b1 = bias_variable([1])

py_x1 = tf.matmul(py_x, w1) + b1
cost1 = tf.losses.mean_squared_error(labels=Y, predictions=py_x1)

lr = 5e-4
train_op1 = tf.train.AdamOptimizer(learning_rate=lr).minimize(cost1)
prediction_error = tf.sqrt(cost1)

# ============================================================= #
def r(a,b):
 r=np.sum((a-np.average(a))*(b-np.average(b)))/math.sqrt(np.sum((a-np.average(a))**2)*np.sum((b-np.average(b))**2))
 return r

def f(o,p,q):
    o_mean = np.average(o)
    a = q-o_mean
    ss = np.sum(a**2)
    b = p-q
    press = np.sum(b**2)
    f = 1 - press/ss
    return f

##################################################################
# ==================== training part =============================
##################################################################
SAVER_DIR = "model2"
saver = tf.train.Saver()
ckpt_path = os.path.join(SAVER_DIR, "model2")
ckpt = tf.train.get_checkpoint_state(SAVER_DIR)
#######################################################################################################################################################
'''
with tf.Session() as sess:
    sess.run(tf.global_variables_initializer())
    best_rmse = 10
    best_idx = 0
    plotdata = []
    plotval = []
    for i in range(100):
        training_batch = zip(range(0, len(train_x), batch_size),
                             range(batch_size, len(train_x) + 1, batch_size))
        # for start, end in tqdm.tqdm(training_batch):
        for start, end in training_batch:
            sess.run(train_op1, feed_dict={X: train_x[start:end], Y: train_y[start:end], p_keep_conv: 0.5})

        loss = sess.run(prediction_error, feed_dict={X: train_x, Y: train_y, p_keep_conv: 0.5})
        plotdata.append(loss)

        merr_valid = sess.run(prediction_error, feed_dict={X: valid_x, Y: valid_y, p_keep_conv: 1.0})
        plotval.append(merr_valid)

        # print validation loss
        if i % 10 == 0:
            print(i, merr_valid)

        if best_rmse > merr_valid:
            best_idx = i
            best_rmse = merr_valid
            save_path = saver.save(sess, ckpt_path, global_step=best_idx)
            print('model saved!')

print('best RMSE fp: ')
print(best_rmse)
print("=== %s seconds ===" % (time.time() - start_time))
print('best idx: ' + str(best_idx))
'''
####################################################################################################################################################
####################################################################
# =========================== test part ============================#
####################################################################
saver = tf.train.Saver()
ckpt_path = os.path.join(SAVER_DIR, "model2")
ckpt = tf.train.get_checkpoint_state(SAVER_DIR)
from sklearn.metrics import mean_squared_error,r2_score

with tf.Session() as sess:
    sess.run(tf.global_variables_initializer())

    saver.restore(sess, ckpt.model_checkpoint_path)
    print("model loaded successfully!")
    y_pred = sess.run(py_x1,feed_dict={X: test_x, p_keep_conv: 1})
    y_valid_pred = sess.run(py_x1,feed_dict={X: valid_x, p_keep_conv: 1})
    print("==========   result of test set   ==========")
    print("RMSE = ",np.sqrt(mean_squared_error(test_y, y_pred)))
    print("R = ",r(test_y, y_pred))
    print("R2 = ",r2_score(test_y, y_pred))
    print("Q2 = ",f(train_y, y_pred,test_y))
    print("==========   result of validation set   ==========")
    print("RMSE = ",np.sqrt(mean_squared_error(valid_y, y_valid_pred)))
    print("R = ",r(valid_y, y_valid_pred))
    y_pred = np.squeeze(y_pred)
    y_test = np.squeeze(test_y)
    y_test = np.ravel(y_test)
    y_pred = np.ravel(y_pred)
    y_train_pred = sess.run(py_x1, feed_dict={X: train_x, p_keep_conv: 1})
    plot_scatter(train_y,y_train_pred,y_test,y_pred)
    plt.subplots_adjust(bottom=0.2)
    #plt.title("GraphFP", size=18)
    plt.show()

    y_train_pred = np.squeeze(y_train_pred)
    y_train = np.squeeze(train_y)
    y_train_pred = np.ravel(y_train_pred)
    y_train = np.ravel(y_train)
    dataframe = pd.DataFrame({'y_pce': y_pred,'pce_true':y_test,'error':y_test-y_pred})
    dataframe.to_csv("gra_output_pce.csv", index=False, sep=',')
    dataframe = pd.DataFrame({'y_trainpre': y_train_pred,'train_true':y_train,'error':y_train-y_train_pred})
    dataframe.to_csv("gra_output_pce(train).csv", index=False, sep=',')
