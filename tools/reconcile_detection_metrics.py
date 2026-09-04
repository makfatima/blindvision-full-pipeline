#!/usr/bin/env python3
"""Reconcile the released matched-class confusion matrix with unmatched FPs.

The raw prediction-level log is unavailable, so this script deliberately
computes only quantities supported by the released aggregate artifacts.
It treats each inter-class confusion as one FN for the true class and one FP
for the predicted class, then adds the separately supplied unmatched/background
false detections. It does not fabricate AP/mAP from counts.
"""
import csv, argparse

def load_matrix(path):
    with open(path, newline='') as f:
        rows=list(csv.reader(f))
    header=rows[0][1:]
    vals=[[int(x) for x in r[1:]] for r in rows[1:]]
    return header, vals

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('matrix')
    ap.add_argument('--unmatched-fp', type=int, default=31)
    ap.add_argument('--images', type=int, default=700)
    ap.add_argument('--out')
    a=ap.parse_args()
    classes, m=load_matrix(a.matrix)
    tp=sum(m[i][i] for i in range(len(m)))
    gt=sum(sum(r) for r in m)
    inter=gt-tp
    fp=inter+a.unmatched_fp
    recall=tp/gt if gt else 0
    precision=tp/(tp+fp) if tp+fp else 0
    f1=2*precision*recall/(precision+recall) if precision+recall else 0
    out=[
      ('ground_truth_instances',gt,'reconciled from confusion matrix'),
      ('correct_classifications',tp,'reconciled from diagonal'),
      ('inter_class_confusions',inter,'reconciled from off-diagonal'),
      ('unmatched_background_false_detections',a.unmatched_fp,'supplied aggregate'),
      ('total_false_positive_assignments',fp,'inter-class + unmatched/background'),
      ('matched_class_recall',f'{recall*100:.2f}%','derived'),
      ('pooled_precision_if_interclass_fp_counted',f'{precision*100:.2f}%','derived; not raw-prediction recomputation'),
      ('pooled_f1_if_interclass_fp_counted',f'{f1*100:.2f}%','derived; not raw-prediction recomputation'),
      ('false_positives_per_image',f'{fp/a.images:.3f}', 'derived'),
    ]
    for k,v,n in out: print(f'{k}: {v} [{n}]')
    if a.out:
        with open(a.out,'w',newline='') as f:
            w=csv.writer(f); w.writerow(['Metric','Value','Basis'])
            w.writerows(out)
if __name__=='__main__': main()
