<!-- Archived report: paths and links adapted; see evidence/ORIGIN-MANIFEST.json. -->
# COSMOS3动态迁移：全部实际Thor运行索引

按run.json实测开始时间排序。失败、退化和非晋升实验全部保留；退出码0仅说明进程完成，数值/性能门槛由各独立audit决定。UTC与澳门UTC+8并列；所有筛选收益相对其各自baseline，不自动混算成官方总收益。

实际远程运行记录共37份。完整读取、命令和选择事件见[Workflow逐事件时间线](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/reports/WORKFLOW-CHRONOLOGY.md)。

## 001. screen-dynamic-lt-v1

开始UTC：2026-10-23T19:44:35.846384+00:00；澳门：2026-10-24T03:44:35+08:00；结束UTC：2026-10-23T19:48:41.518826+00:00。

退出码：0；外来GPU干扰：False；profile：none。

实际命令、身份、遥测、日志：[run.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/screen-dynamic-lt-v1/run.json)；Workflow start event：evt-20261023T194433551055Z-d4b6b9de81。

## 002. official-fresh-22-v1

开始UTC：2026-10-23T19:51:22.394624+00:00；澳门：2026-10-24T03:51:22+08:00；结束UTC：2026-10-23T19:54:31.386837+00:00。

退出码：0；外来GPU干扰：False；profile：none。

实际命令、身份、遥测、日志：[run.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/official-fresh-22-v1/run.json)；Workflow start event：evt-20261023T195120062007Z-c3d0b8dc24。

## 003. candidate-full-port-gate-v1

开始UTC：2026-10-23T19:55:40.426966+00:00；澳门：2026-10-24T03:55:40+08:00；结束UTC：2026-10-23T19:58:09.874904+00:00。

退出码：0；外来GPU干扰：False；profile：none。

实际命令、身份、遥测、日志：[run.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/candidate-full-port-gate-v1/run.json)；Workflow start event：evt-20261023T195538091084Z-32a96ad309。

## 004. parent-final-shape-screen-v1

开始UTC：2026-10-23T19:58:55.685554+00:00；澳门：2026-10-24T03:58:55+08:00；结束UTC：2026-10-23T20:02:31.985326+00:00。

退出码：0；外来GPU干扰：False；profile：none。

实际命令、身份、遥测、日志：[run.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/parent-final-shape-screen-v1/run.json)；Workflow start event：evt-20261023T195853353081Z-765820b244。

证据：[本次paired-full-port-e2e.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/parent-final-shape-screen-v1/paired-full-port-e2e.json)

```json
{
  "complete": true,
  "gate_passed": true,
  "summary": {
    "0": {
      "samples": 9,
      "baseline_median_ms": 2810.6663189828396,
      "candidate_median_ms": 3084.174052113667,
      "reduction_from_medians_pct": -9.731063815138619,
      "paired_median_reduction_pct": -5.296437330716652,
      "reduction_from_total_time_pct": -3.1025247150911817,
      "all_bytes_equal": true,
      "by_case": {
        "video320x512": {
          "samples": 3,
          "baseline_median_ms": 2246.429896913469,
          "candidate_median_ms": 1965.8049191348255,
          "reduction_from_medians_pct": 12.492042514400925,
          "paired_median_reduction_pct": 12.492042514400925,
          "reduction_from_total_time_pct": 12.39646212038874,
          "all_bytes_equal": true
        },
        "video17frames": {
          "samples": 3,
          "baseline_median_ms": 2810.6663189828396,
          "candidate_median_ms": 3084.174052113667,
          "reduction_from_medians_pct": -9.731063815138619,
          "paired_median_reduction_pct": -9.731063815138619,
          "reduction_from_total_time_pct": -8.773317486846022,
          "all_bytes_equal": true
        },
        "action16": {
          "samples": 3,
          "baseline_median_ms": 5549.872410017997,
          "candidate_median_ms": 5941.341379890218,
          "reduction_from_medians_pct": -7.0536571104875545,
          "paired_median_reduction_pct": -5.296437330716652,
          "reduction_from_total_time_pct": -6.502685606441094,
          "all_bytes_equal": true
        }
      }
    },
    "1": {
      "samples": 9,
      "baseline_median_ms": 2846.065682126209,
      "candidate_median_ms": 3121.252943063155,
      "reduction_from_medians_pct": -9.669041114025223,
      "paired_median_reduction_pct": -5.972097992703906,
      "reduction_from_total_time_pct": -3.706017993927224,
      "all_bytes_equal": true,
      "by_case": {
        "video320x512": {
          "samples": 3,
          "baseline_median_ms": 2270.0507638510317,
          "candidate_median_ms": 2110.434150090441,
          "reduction_from_medians_pct": 7.03141164516553,
          "paired_median_reduction_pct": 8.084868046767934,
          "reduction_from_total_time_pct": 8.459219888058634,
          "all_bytes_equal": true
        },
        "video17frames": {
          "samples": 3,
          "baseline_median_ms": 2846.065682126209,
          "candidate_median_ms": 3121.252943063155,
          "reduction_from_medians_pct": -9.669041114025223,
          "paired_median_reduction_pct": -9.597973212728972,
          "reduction_from_total_time_pct": -9.828102640834867,
          "all_bytes_equal": true
        },
        "action16": {
          "samples": 3,
          "baseline_median_ms": 5761.310262838379,
          "candidate_median_ms": 6061.109950067475,
          "reduction_from_medians_pct": -5.20367196960152,
          "paired_median_reduction_pct": -5.972097992703906,
          "reduction_from_total_time_pct": -5.534796209873694,
          "all_bytes_equal": true
        }
      }
    }
  },
  "pairs_count": 18,
  "rows_count": 36
}
```

## 005. category-e2e-screen-v1

开始UTC：2026-10-23T20:04:48.450274+00:00；澳门：2026-10-24T04:04:48+08:00；结束UTC：2026-10-23T20:09:51.034281+00:00。

退出码：0；外来GPU干扰：False；profile：none。

实际命令、身份、遥测、日志：[run.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/category-e2e-screen-v1/run.json)；Workflow start event：evt-20261023T200446072725Z-665cc81f44。

## 006. candidate-full-port-gate-v2

开始UTC：2026-10-23T20:12:39.183853+00:00；澳门：2026-10-24T04:12:39+08:00；结束UTC：2026-10-23T20:15:07.067826+00:00。

退出码：0；外来GPU干扰：False；profile：none。

实际命令、身份、遥测、日志：[run.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/candidate-full-port-gate-v2/run.json)；Workflow start event：evt-20261023T201236860491Z-46461160ad。

## 007. parent-final-shape-screen-v2

开始UTC：2026-10-23T20:15:31.090465+00:00；澳门：2026-10-24T04:15:31+08:00；结束UTC：2026-10-23T20:19:52.723450+00:00。

退出码：0；外来GPU干扰：False；profile：none。

实际命令、身份、遥测、日志：[run.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/parent-final-shape-screen-v2/run.json)；Workflow start event：evt-20261023T201528798983Z-f977d53b2a。

证据：[本次paired-full-port-e2e.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/parent-final-shape-screen-v2/paired-full-port-e2e.json)

```json
{
  "complete": true,
  "gate_passed": true,
  "summary": {
    "0": {
      "samples": 12,
      "baseline_median_ms": 2875.0070250825956,
      "candidate_median_ms": 2834.711885661818,
      "reduction_from_medians_pct": 1.401566642071772,
      "paired_median_reduction_pct": 2.1674643484741463,
      "reduction_from_total_time_pct": 2.874475479623173,
      "all_bytes_equal": true,
      "by_case": {
        "video320x512": {
          "samples": 4,
          "baseline_median_ms": 2296.4942374965176,
          "candidate_median_ms": 2051.7981734592468,
          "reduction_from_medians_pct": 10.65520043734235,
          "paired_median_reduction_pct": 10.626073051749469,
          "reduction_from_total_time_pct": 10.674379940851475,
          "all_bytes_equal": true
        },
        "video17frames": {
          "samples": 4,
          "baseline_median_ms": 2875.0070250825956,
          "candidate_median_ms": 2834.711885661818,
          "reduction_from_medians_pct": 1.401566642071772,
          "paired_median_reduction_pct": 1.401897789104456,
          "reduction_from_total_time_pct": 1.2893342699006882,
          "all_bytes_equal": true
        },
        "action16": {
          "samples": 4,
          "baseline_median_ms": 5783.327520010062,
          "candidate_median_ms": 5786.660294048488,
          "reduction_from_medians_pct": -0.05762727472886642,
          "paired_median_reduction_pct": -0.5053127214137809,
          "reduction_from_total_time_pct": 0.5193402872997854,
          "all_bytes_equal": true
        }
      }
    },
    "1": {
      "samples": 12,
      "baseline_median_ms": 2904.4271796010435,
      "candidate_median_ms": 2944.3173540057614,
      "reduction_from_medians_pct": -1.3734265635882537,
      "paired_median_reduction_pct": 3.7279232471578885,
      "reduction_from_total_time_pct": 2.19736237065693,
      "all_bytes_equal": true,
      "by_case": {
        "video320x512": {
          "samples": 4,
          "baseline_median_ms": 2322.374721406959,
          "candidate_median_ms": 2115.906340070069,
          "reduction_from_medians_pct": 8.890399100271207,
          "paired_median_reduction_pct": 8.831111967157002,
          "reduction_from_total_time_pct": 9.811507206399794,
          "all_bytes_equal": true
        },
        "video17frames": {
          "samples": 4,
          "baseline_median_ms": 2904.4271796010435,
          "candidate_median_ms": 2944.3173540057614,
          "reduction_from_medians_pct": -1.3734265635882537,
          "paired_median_reduction_pct": 0.03498456649632109,
          "reduction_from_total_time_pct": 0.47012204061076535,
          "all_bytes_equal": true
        },
        "action16": {
          "samples": 4,
          "baseline_median_ms": 5678.54563461151,
          "candidate_median_ms": 5670.80748511944,
          "reduction_from_medians_pct": 0.13626991821471535,
          "paired_median_reduction_pct": 0.23435559782741255,
          "reduction_from_total_time_pct": -0.07389053262449874,
          "all_bytes_equal": true
        }
      }
    }
  },
  "pairs_count": 24,
  "rows_count": 48
}
```

## 008. candidate-full-port-gate-v3

开始UTC：2026-10-23T20:21:27.950886+00:00；澳门：2026-10-24T04:21:27+08:00；结束UTC：2026-10-23T20:23:59.911951+00:00。

退出码：0；外来GPU干扰：False；profile：none。

实际命令、身份、遥测、日志：[run.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/candidate-full-port-gate-v3/run.json)；Workflow start event：evt-20261023T202125644759Z-578989e744。

## 009. formal-main-v3-window0

开始UTC：2026-10-23T20:26:09.556852+00:00；澳门：2026-10-24T04:26:09+08:00；结束UTC：2026-10-23T20:34:43.902426+00:00。

退出码：0；外来GPU干扰：False；profile：none。

实际命令、身份、遥测、日志：[run.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/formal-main-v3-window0/run.json)；Workflow start event：evt-20261023T202607262987Z-35c1fc1d7b。

证据：[本次paired-full-port-e2e.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/formal-main-v3-window0/paired-full-port-e2e.json)

```json
{
  "complete": true,
  "gate_passed": true,
  "summary": {
    "0": {
      "samples": 20,
      "baseline_median_ms": 8586.585407960229,
      "candidate_median_ms": 6027.4994923966005,
      "reduction_from_medians_pct": 29.803301242321744,
      "paired_median_reduction_pct": 30.068914499511223,
      "reduction_from_total_time_pct": 29.376614879258657,
      "all_bytes_equal": true,
      "by_case": {
        "len31_17": {
          "samples": 5,
          "baseline_median_ms": 8493.506310973316,
          "candidate_median_ms": 5938.712396891788,
          "reduction_from_medians_pct": 30.07937853393743,
          "paired_median_reduction_pct": 30.58596477181036,
          "reduction_from_total_time_pct": 31.217775148819204,
          "all_bytes_equal": true
        },
        "len65_97": {
          "samples": 5,
          "baseline_median_ms": 8534.334430005401,
          "candidate_median_ms": 6303.006103029475,
          "reduction_from_medians_pct": 26.145311567952167,
          "paired_median_reduction_pct": 26.819142378699713,
          "reduction_from_total_time_pct": 27.42538173617649,
          "all_bytes_equal": true
        },
        "len128_129": {
          "samples": 5,
          "baseline_median_ms": 8560.254395008087,
          "candidate_median_ms": 5987.174567999318,
          "reduction_from_medians_pct": 30.058450465085016,
          "paired_median_reduction_pct": 30.291966548437877,
          "reduction_from_total_time_pct": 30.67295426941441,
          "all_bytes_equal": true
        },
        "len257_7": {
          "samples": 5,
          "baseline_median_ms": 8743.563893949613,
          "candidate_median_ms": 6280.06705804728,
          "reduction_from_medians_pct": 28.174973795376822,
          "paired_median_reduction_pct": 27.780433252535875,
          "reduction_from_total_time_pct": 28.22033110277532,
          "all_bytes_equal": true
        }
      }
    }
  },
  "pairs_count": 20,
  "rows_count": 48
}
```

## 010. formal-main-v3-window1

开始UTC：2026-10-23T20:34:46.532596+00:00；澳门：2026-10-24T04:34:46+08:00；结束UTC：2026-10-23T20:43:35.099892+00:00。

退出码：0；外来GPU干扰：False；profile：none。

实际命令、身份、遥测、日志：[run.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/formal-main-v3-window1/run.json)；Workflow start event：evt-20261023T203444249385Z-3bec662e08。

证据：[本次paired-full-port-e2e.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/formal-main-v3-window1/paired-full-port-e2e.json)

```json
{
  "complete": true,
  "gate_passed": true,
  "summary": {
    "1": {
      "samples": 20,
      "baseline_median_ms": 8676.979701966047,
      "candidate_median_ms": 6198.705680551939,
      "reduction_from_medians_pct": 28.561482296110206,
      "paired_median_reduction_pct": 28.77735237551297,
      "reduction_from_total_time_pct": 28.28211109643316,
      "all_bytes_equal": true,
      "by_case": {
        "len31_17": {
          "samples": 5,
          "baseline_median_ms": 8692.359712906182,
          "candidate_median_ms": 6371.615543961525,
          "reduction_from_medians_pct": 26.698666939644454,
          "paired_median_reduction_pct": 28.115737985852395,
          "reduction_from_total_time_pct": 27.96124362262932,
          "all_bytes_equal": true
        },
        "len65_97": {
          "samples": 5,
          "baseline_median_ms": 8565.138038946316,
          "candidate_median_ms": 6087.742642033845,
          "reduction_from_medians_pct": 28.92417361690577,
          "paired_median_reduction_pct": 29.26228813361067,
          "reduction_from_total_time_pct": 29.440691513213444,
          "all_bytes_equal": true
        },
        "len128_129": {
          "samples": 5,
          "baseline_median_ms": 8746.899254852906,
          "candidate_median_ms": 6435.026234947145,
          "reduction_from_medians_pct": 26.430772237637246,
          "paired_median_reduction_pct": 26.38030159273096,
          "reduction_from_total_time_pct": 26.11227039722237,
          "all_bytes_equal": true
        },
        "len257_7": {
          "samples": 5,
          "baseline_median_ms": 8661.599691025913,
          "candidate_median_ms": 6108.437462942675,
          "reduction_from_medians_pct": 29.476797810553535,
          "paired_median_reduction_pct": 29.406691556657616,
          "reduction_from_total_time_pct": 29.634775704929517,
          "all_bytes_equal": true
        }
      }
    }
  },
  "pairs_count": 20,
  "rows_count": 48
}
```

## 011. formal-shapes-v3-window0

开始UTC：2026-10-23T20:43:37.747403+00:00；澳门：2026-10-24T04:43:37+08:00；结束UTC：2026-10-23T20:49:05.867196+00:00。

退出码：0；外来GPU干扰：False；profile：none。

实际命令、身份、遥测、日志：[run.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/formal-shapes-v3-window0/run.json)；Workflow start event：evt-20261023T204335443182Z-5f81a5e91d。

证据：[本次paired-full-port-e2e.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/formal-shapes-v3-window0/paired-full-port-e2e.json)

```json
{
  "complete": true,
  "gate_passed": true,
  "summary": {
    "0": {
      "samples": 21,
      "baseline_median_ms": 4211.11875702627,
      "candidate_median_ms": 3002.529555000365,
      "reduction_from_medians_pct": 28.69995532682067,
      "paired_median_reduction_pct": 30.392955927015574,
      "reduction_from_total_time_pct": 31.516219913395606,
      "all_bytes_equal": true,
      "by_case": {
        "video320x512": {
          "samples": 7,
          "baseline_median_ms": 3282.8048241790384,
          "candidate_median_ms": 2279.9954938236624,
          "reduction_from_medians_pct": 30.547333273343714,
          "paired_median_reduction_pct": 29.90510566538357,
          "reduction_from_total_time_pct": 29.336439711880878,
          "all_bytes_equal": true
        },
        "video17frames": {
          "samples": 7,
          "baseline_median_ms": 4211.11875702627,
          "candidate_median_ms": 3002.529555000365,
          "reduction_from_medians_pct": 28.69995532682067,
          "paired_median_reduction_pct": 29.45708864418375,
          "reduction_from_total_time_pct": 28.73373354392249,
          "all_bytes_equal": true
        },
        "action16": {
          "samples": 7,
          "baseline_median_ms": 8694.043608848006,
          "candidate_median_ms": 5583.74147885479,
          "reduction_from_medians_pct": 35.77509234975349,
          "paired_median_reduction_pct": 35.38069414505644,
          "reduction_from_total_time_pct": 33.69192471154101,
          "all_bytes_equal": true
        }
      }
    }
  },
  "pairs_count": 21,
  "rows_count": 50
}
```

## 012. formal-shapes-v3-window1

开始UTC：2026-10-23T20:49:08.500707+00:00；澳门：2026-10-24T04:49:08+08:00；结束UTC：2026-10-23T20:54:36.409312+00:00。

退出码：0；外来GPU干扰：False；profile：none。

实际命令、身份、遥测、日志：[run.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/formal-shapes-v3-window1/run.json)；Workflow start event：evt-20261023T204906191830Z-283d2ed1f8。

证据：[本次paired-full-port-e2e.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/formal-shapes-v3-window1/paired-full-port-e2e.json)

```json
{
  "complete": true,
  "gate_passed": true,
  "summary": {
    "1": {
      "samples": 21,
      "baseline_median_ms": 4210.034799994901,
      "candidate_median_ms": 2978.911496931687,
      "reduction_from_medians_pct": 29.24259208177341,
      "paired_median_reduction_pct": 30.80008490951297,
      "reduction_from_total_time_pct": 30.724352781585097,
      "all_bytes_equal": true,
      "by_case": {
        "video320x512": {
          "samples": 7,
          "baseline_median_ms": 3307.717530056834,
          "candidate_median_ms": 2300.3311208449304,
          "reduction_from_medians_pct": 30.455635950104675,
          "paired_median_reduction_pct": 29.59438357487286,
          "reduction_from_total_time_pct": 29.321829010516332,
          "all_bytes_equal": true
        },
        "video17frames": {
          "samples": 7,
          "baseline_median_ms": 4210.034799994901,
          "candidate_median_ms": 2978.911496931687,
          "reduction_from_medians_pct": 29.24259208177341,
          "paired_median_reduction_pct": 29.36445009562171,
          "reduction_from_total_time_pct": 29.646697226741047,
          "all_bytes_equal": true
        },
        "action16": {
          "samples": 7,
          "baseline_median_ms": 8685.64874283038,
          "candidate_median_ms": 5911.8724630679935,
          "reduction_from_medians_pct": 31.93516525811635,
          "paired_median_reduction_pct": 32.360520315071426,
          "reduction_from_total_time_pct": 31.779452833720732,
          "all_bytes_equal": true
        }
      }
    }
  },
  "pairs_count": 21,
  "rows_count": 50
}
```

## 013. graph-fallback-full-port-v3

开始UTC：2026-10-23T20:54:39.034892+00:00；澳门：2026-10-24T04:54:39+08:00；结束UTC：2026-10-23T20:55:25.651655+00:00。

退出码：0；外来GPU干扰：False；profile：none。

实际命令、身份、遥测、日志：[run.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/graph-fallback-full-port-v3/run.json)；Workflow start event：evt-20261023T205436727379Z-f9b2720915。

证据：[本次graph-fallback-validation.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/graph-fallback-full-port-v3/graph-fallback-validation.json)

```json
{
  "complete": true,
  "gate_passed": true,
  "rows_count": 4
}
```

## 014. profile-full-port-v3

开始UTC：2026-10-23T20:55:28.223021+00:00；澳门：2026-10-24T04:55:28+08:00；结束UTC：2026-10-23T20:56:23.501112+00:00。

退出码：0；外来GPU干扰：False；profile：none。

实际命令、身份、遥测、日志：[run.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/profile-full-port-v3/run.json)；Workflow start event：evt-20261023T205525947252Z-2a59150cdd。

证据：[本次profile-metadata.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/profile-full-port-v3/profile-metadata.json)

```json
{
  "complete": true,
  "byte_equal": true
}
```

## 015. m3542-lt-screen-v1

开始UTC：2026-10-23T20:58:04.290904+00:00；澳门：2026-10-24T04:58:04+08:00；结束UTC：2026-10-23T20:58:56.992747+00:00。

退出码：0；外来GPU干扰：False；profile：none。

实际命令、身份、遥测、日志：[run.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/m3542-lt-screen-v1/run.json)；Workflow start event：evt-20261023T205801976413Z-9d776efc82。

## 016. main-route-e2e-screen-v2

开始UTC：2026-10-23T21:02:01.373132+00:00；澳门：2026-10-24T05:02:01+08:00；结束UTC：2026-10-23T21:04:33.304241+00:00。

退出码：0；外来GPU干扰：False；profile：none。

实际命令、身份、遥测、日志：[run.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/main-route-e2e-screen-v2/run.json)；Workflow start event：evt-20261023T210159083540Z-564368cb29。

## 017. profile-main-full-port-v3

开始UTC：2026-10-23T21:06:01.149956+00:00；澳门：2026-10-24T05:06:01+08:00；结束UTC：2026-10-23T21:07:01.208208+00:00。

退出码：0；外来GPU干扰：False；profile：none。

实际命令、身份、遥测、日志：[run.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/profile-main-full-port-v3/run.json)；Workflow start event：evt-20261023T210558829854Z-3147572175。

证据：[本次profile-metadata.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/profile-main-full-port-v3/profile-metadata.json)

```json
{
  "complete": true,
  "byte_equal": true
}
```

## 018. main-route-per-category-screen-v3

开始UTC：2026-10-23T21:07:51.193056+00:00；澳门：2026-10-24T05:07:51+08:00；结束UTC：2026-10-23T21:12:22.063499+00:00。

退出码：0；外来GPU干扰：False；profile：none。

实际命令、身份、遥测、日志：[run.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/main-route-per-category-screen-v3/run.json)；Workflow start event：evt-20261023T210748874297Z-1d9a4a68bc。

## 019. cfg-gemm-batch-feasibility-v1

开始UTC：2026-10-23T21:12:42.749797+00:00；澳门：2026-10-24T05:12:42+08:00；结束UTC：2026-10-23T21:13:30.179222+00:00。

退出码：0；外来GPU干扰：False；profile：none。

实际命令、身份、遥测、日志：[run.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/cfg-gemm-batch-feasibility-v1/run.json)；Workflow start event：evt-20261023T211240456343Z-c4e58d0ead。

## 020. sampler-residency-screen-v1

开始UTC：2026-10-23T21:25:02.744585+00:00；澳门：2026-10-24T05:25:02+08:00；结束UTC：2026-10-23T21:25:03.158351+00:00。

退出码：1；外来GPU干扰：False；profile：none。

实际命令、身份、遥测、日志：[run.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/sampler-residency-screen-v1/run.json)；Workflow start event：evt-20261023T212500456961Z-e963a85df0。

## 021. sampler-residency-screen-v1-attempt2

开始UTC：2026-10-23T21:25:57.965159+00:00；澳门：2026-10-24T05:25:57+08:00；结束UTC：2026-10-23T21:28:04.295059+00:00。

退出码：0；外来GPU干扰：False；profile：none。

实际命令、身份、遥测、日志：[run.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/sampler-residency-screen-v1-attempt2/run.json)；Workflow start event：evt-20261023T212555652856Z-e78741ceeb。

证据：[本次independent-screen-audit.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/sampler-residency-screen-v1-attempt2/independent-screen-audit.json)

```json
{
  "complete": true,
  "results": [
    {
      "variant": "sigma",
      "gate_passed": true,
      "pairs": 4,
      "paired_median_reduction_pct": 0.053298438014892646,
      "reduction_from_total_time_pct": -0.5388651312276949,
      "accepted_for_confirmation": false
    },
    {
      "variant": "sigma_constants",
      "gate_passed": false,
      "pairs": 0,
      "rejection": "byte/residency/physical-dispatch warmup gate",
      "accepted_for_confirmation": false
    }
  ]
}
```

## 022. request-residency-screen-v4-window0

开始UTC：2026-10-23T21:30:22.199811+00:00；澳门：2026-10-24T05:30:22+08:00；结束UTC：2026-10-23T21:34:33.676788+00:00。

退出码：0；外来GPU干扰：False；profile：none。

实际命令、身份、遥测、日志：[run.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/request-residency-screen-v4-window0/run.json)；Workflow start event：evt-20261023T213019873100Z-fb9e518dcf。

证据：[本次independent-screen-audit.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/request-residency-screen-v4-window0/independent-screen-audit.json)

```json
{
  "complete": true,
  "screen_only": true,
  "results": [
    {
      "variant": "sigma_constants",
      "gate_passed": true,
      "pairs": 4,
      "paired_median_reduction_pct": 0.019758297283217763,
      "reduction_from_total_time_pct": 1.2086542904506614,
      "accepted_for_confirmation": false,
      "actual_failed_rows": []
    },
    {
      "variant": "key_ahead",
      "gate_passed": true,
      "pairs": 4,
      "paired_median_reduction_pct": 1.3059128313498036,
      "reduction_from_total_time_pct": 1.6061165755454465,
      "accepted_for_confirmation": true,
      "actual_failed_rows": []
    },
    {
      "variant": "sigma_constants_key_ahead",
      "gate_passed": true,
      "pairs": 4,
      "paired_median_reduction_pct": -0.18299859005962982,
      "reduction_from_total_time_pct": -1.111758206470137,
      "accepted_for_confirmation": false,
      "actual_failed_rows": []
    }
  ]
}
```

## 023. request-coefficients-screen-v1-window0

开始UTC：2026-10-23T21:35:07.300652+00:00；澳门：2026-10-24T05:35:07+08:00；结束UTC：2026-10-23T21:38:05.411931+00:00。

退出码：0；外来GPU干扰：False；profile：none。

实际命令、身份、遥测、日志：[run.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/request-coefficients-screen-v1-window0/run.json)；Workflow start event：evt-20261023T213504484468Z-604eba9364。

证据：[本次independent-screen-audit.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/request-coefficients-screen-v1-window0/independent-screen-audit.json)

```json
{
  "complete": true,
  "screen_only": true,
  "results": [
    {
      "variant": "coefficients",
      "gate_passed": true,
      "pairs": 4,
      "paired_median_reduction_pct": -0.2969167638944836,
      "reduction_from_total_time_pct": 0.6146997553005962,
      "accepted_for_confirmation": false,
      "actual_failed_rows": []
    },
    {
      "variant": "coefficients_key_ahead",
      "gate_passed": true,
      "pairs": 4,
      "paired_median_reduction_pct": 0.6937387933554306,
      "reduction_from_total_time_pct": -0.5806573966783413,
      "accepted_for_confirmation": false,
      "actual_failed_rows": []
    }
  ]
}
```

## 024. key-ahead-independent-window1

开始UTC：2026-10-23T21:40:20.832027+00:00；澳门：2026-10-24T05:40:20+08:00；结束UTC：2026-10-23T21:43:01.111904+00:00。

退出码：0；外来GPU干扰：False；profile：none。

实际命令、身份、遥测、日志：[run.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/key-ahead-independent-window1/run.json)；Workflow start event：evt-20261023T214018538179Z-4bb16f2d2f。

证据：[本次independent-screen-audit.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/key-ahead-independent-window1/independent-screen-audit.json)

```json
{
  "complete": true,
  "screen_only": true,
  "results": [
    {
      "variant": "key_ahead",
      "gate_passed": true,
      "pairs": 8,
      "paired_median_reduction_pct": -0.03672851073527328,
      "reduction_from_total_time_pct": 0.037468213209046475,
      "accepted_for_confirmation": false,
      "actual_failed_rows": []
    }
  ]
}
```

## 025. opposite-layout-main-screen-v1

开始UTC：2026-10-23T21:43:35.544636+00:00；澳门：2026-10-24T05:43:35+08:00；结束UTC：2026-10-23T21:44:26.090610+00:00。

退出码：0；外来GPU干扰：False；profile：none。

实际命令、身份、遥测、日志：[run.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/opposite-layout-main-screen-v1/run.json)；Workflow start event：evt-20261023T214333236858Z-4933e21efa。

证据：[本次independent-screen-audit.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/opposite-layout-main-screen-v1/independent-screen-audit.json)

```json
{
  "complete": true,
  "screen_only": true,
  "rows_count": 4,
  "results": []
}
```

## 026. opposite-layout-e2e-screen-v1-window0

开始UTC：2026-10-23T21:47:27.166784+00:00；澳门：2026-10-24T05:47:27+08:00；结束UTC：2026-10-23T21:50:23.206081+00:00。

退出码：0；外来GPU干扰：False；profile：none。

实际命令、身份、遥测、日志：[run.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/opposite-layout-e2e-screen-v1-window0/run.json)；Workflow start event：evt-20261023T214724841366Z-1474f12b1a。

证据：[本次independent-screen-audit.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/opposite-layout-e2e-screen-v1-window0/independent-screen-audit.json)

```json
{
  "complete": true,
  "all_bytes_phases_dispatch_passed": true,
  "screen_only": true,
  "results": [
    {
      "variant": "selected_all",
      "pairs": 4,
      "gate_passed": true,
      "paired_median_reduction_pct": -4.070494127732971,
      "reduction_from_total_time_pct": -3.550702620610169,
      "accepted_for_confirmation": false,
      "orders": [
        [
          "inherited",
          "selected_all"
        ],
        [
          "selected_all",
          "inherited"
        ],
        [
          "inherited",
          "selected_all"
        ],
        [
          "selected_all",
          "inherited"
        ]
      ]
    },
    {
      "variant": "selected_out_torch_down",
      "pairs": 4,
      "gate_passed": true,
      "paired_median_reduction_pct": 8.222649697512235,
      "reduction_from_total_time_pct": 8.656160753042286,
      "accepted_for_confirmation": true,
      "orders": [
        [
          "inherited",
          "selected_out_torch_down"
        ],
        [
          "selected_out_torch_down",
          "inherited"
        ],
        [
          "inherited",
          "selected_out_torch_down"
        ],
        [
          "selected_out_torch_down",
          "inherited"
        ]
      ]
    }
  ]
}
```

## 027. opposite-layout-e2e-confirm-v2-window1

开始UTC：2026-10-23T21:52:09.699813+00:00；澳门：2026-10-24T05:52:09+08:00；结束UTC：2026-10-23T21:54:45.635154+00:00。

退出码：0；外来GPU干扰：False；profile：none。

实际命令、身份、遥测、日志：[run.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/opposite-layout-e2e-confirm-v2-window1/run.json)；Workflow start event：evt-20261023T215207380035Z-384dd71c6a。

证据：[本次independent-screen-audit.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/opposite-layout-e2e-confirm-v2-window1/independent-screen-audit.json)

```json
{
  "complete": true,
  "all_bytes_phases_dispatch_passed": true,
  "screen_only": true,
  "results": [
    {
      "variant": "selected_out_torch_down",
      "pairs": 8,
      "gate_passed": true,
      "paired_median_reduction_pct": 7.027465213380896,
      "reduction_from_total_time_pct": 6.774878375335702,
      "accepted_for_confirmation": true,
      "orders": [
        [
          "selected_out_torch_down",
          "inherited"
        ],
        [
          "inherited",
          "selected_out_torch_down"
        ],
        [
          "selected_out_torch_down",
          "inherited"
        ],
        [
          "inherited",
          "selected_out_torch_down"
        ],
        [
          "selected_out_torch_down",
          "inherited"
        ],
        [
          "inherited",
          "selected_out_torch_down"
        ],
        [
          "selected_out_torch_down",
          "inherited"
        ],
        [
          "inherited",
          "selected_out_torch_down"
        ]
      ]
    }
  ]
}
```

## 028. candidate-gate-v4

开始UTC：2026-10-23T21:56:42.733663+00:00；澳门：2026-10-24T05:56:42+08:00；结束UTC：2026-10-23T21:59:08.777425+00:00。

退出码：0；外来GPU干扰：False；profile：none。

实际命令、身份、遥测、日志：[run.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/candidate-gate-v4/run.json)；Workflow start event：evt-20261023T215640177463Z-7519461923。

证据：[本次validation.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/candidate-gate-v4/validation.json)

```json
{
  "complete": true,
  "exact_gate_passed": true,
  "cases_count": 25
}
```

## 029. official-extra-main-v4

开始UTC：2026-10-23T22:00:15.351870+00:00；澳门：2026-10-24T06:00:15+08:00；结束UTC：2026-10-23T22:01:07.159888+00:00。

退出码：0；外来GPU干扰：False；profile：none。

实际命令、身份、遥测、日志：[run.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/official-extra-main-v4/run.json)；Workflow start event：evt-20261023T220013068702Z-dcc8d7afa6。

证据：[本次validation.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/official-extra-main-v4/validation.json)

```json
{
  "complete": true,
  "exact_gate_passed": true,
  "cases_count": 2
}
```

## 030. candidate-extra-main-v4

开始UTC：2026-10-23T22:01:36.498236+00:00；澳门：2026-10-24T06:01:36+08:00；结束UTC：2026-10-23T22:02:20.824281+00:00。

退出码：1；外来GPU干扰：False；profile：none。

实际命令、身份、遥测、日志：[run.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/candidate-extra-main-v4/run.json)；Workflow start event：evt-20261023T220134220937Z-2e3e683090。

证据：[本次validation.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/candidate-extra-main-v4/validation.json)

```json
{
  "complete": false,
  "exact_gate_passed": false,
  "cases_count": 0
}
```

## 031. candidate-extra-main-v4-attempt2

开始UTC：2026-10-23T22:05:04.558552+00:00；澳门：2026-10-24T06:05:04+08:00；结束UTC：2026-10-23T22:06:07.858831+00:00。

退出码：0；外来GPU干扰：False；profile：none。

实际命令、身份、遥测、日志：[run.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/candidate-extra-main-v4-attempt2/run.json)；Workflow start event：evt-20261023T220502225105Z-c05a4b0291。

证据：[本次validation.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/candidate-extra-main-v4-attempt2/validation.json)

```json
{
  "complete": true,
  "exact_gate_passed": true,
  "cases_count": 4
}
```

## 032. formal-main-v4-window0

开始UTC：2026-10-23T22:07:05.082432+00:00；澳门：2026-10-24T06:07:05+08:00；结束UTC：2026-10-23T22:15:36.074610+00:00。

退出码：0；外来GPU干扰：False；profile：none。

实际命令、身份、遥测、日志：[run.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/formal-main-v4-window0/run.json)；Workflow start event：evt-20261023T220702792459Z-9a33f89b80。

证据：[本次paired-full-port-e2e.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/formal-main-v4-window0/paired-full-port-e2e.json)

```json
{
  "complete": true,
  "gate_passed": true,
  "summary": {
    "0": {
      "samples": 20,
      "baseline_median_ms": 8622.931401012465,
      "candidate_median_ms": 5785.138312494382,
      "reduction_from_medians_pct": 32.909841868681475,
      "paired_median_reduction_pct": 32.79641430537649,
      "reduction_from_total_time_pct": 32.57589512145098,
      "all_bytes_equal": true,
      "by_case": {
        "len31_17": {
          "samples": 5,
          "baseline_median_ms": 8458.80459412001,
          "candidate_median_ms": 5647.720290115103,
          "reduction_from_medians_pct": 33.232642659211955,
          "paired_median_reduction_pct": 34.15833232286018,
          "reduction_from_total_time_pct": 34.207528684184894,
          "all_bytes_equal": true
        },
        "len65_97": {
          "samples": 5,
          "baseline_median_ms": 8686.83676701039,
          "candidate_median_ms": 5946.239585988224,
          "reduction_from_medians_pct": 31.548850916941483,
          "paired_median_reduction_pct": 31.5130252565732,
          "reduction_from_total_time_pct": 32.22371795465764,
          "all_bytes_equal": true
        },
        "len128_129": {
          "samples": 5,
          "baseline_median_ms": 8548.3239130117,
          "candidate_median_ms": 5744.2465629428625,
          "reduction_from_medians_pct": 32.80265673836546,
          "paired_median_reduction_pct": 33.51840228300013,
          "reduction_from_total_time_pct": 33.05066695409109,
          "all_bytes_equal": true
        },
        "len257_7": {
          "samples": 5,
          "baseline_median_ms": 8685.116312932223,
          "candidate_median_ms": 6073.169614886865,
          "reduction_from_medians_pct": 30.07382519628602,
          "paired_median_reduction_pct": 29.54012350077958,
          "reduction_from_total_time_pct": 30.85674007114537,
          "all_bytes_equal": true
        }
      }
    }
  },
  "pairs_count": 20,
  "rows_count": 48
}
```

## 033. formal-main-v4-window1

开始UTC：2026-10-23T22:15:38.734663+00:00；澳门：2026-10-24T06:15:38+08:00；结束UTC：2026-10-23T22:24:21.181599+00:00。

退出码：0；外来GPU干扰：False；profile：none。

实际命令、身份、遥测、日志：[run.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/formal-main-v4-window1/run.json)；Workflow start event：evt-20261023T221536413488Z-f6c676339e。

证据：[本次paired-full-port-e2e.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/formal-main-v4-window1/paired-full-port-e2e.json)

```json
{
  "complete": true,
  "gate_passed": true,
  "summary": {
    "1": {
      "samples": 20,
      "baseline_median_ms": 8664.227228029631,
      "candidate_median_ms": 5924.618287943304,
      "reduction_from_medians_pct": 31.61977251962439,
      "paired_median_reduction_pct": 30.741611559037874,
      "reduction_from_total_time_pct": 30.495354225347505,
      "all_bytes_equal": true,
      "by_case": {
        "len31_17": {
          "samples": 5,
          "baseline_median_ms": 8710.41655400768,
          "candidate_median_ms": 6123.493019025773,
          "reduction_from_medians_pct": 29.699194280113485,
          "paired_median_reduction_pct": 30.227710568734565,
          "reduction_from_total_time_pct": 30.159329084269228,
          "all_bytes_equal": true
        },
        "len65_97": {
          "samples": 5,
          "baseline_median_ms": 8527.797110145912,
          "candidate_median_ms": 5885.201327968389,
          "reduction_from_medians_pct": 30.988023613196724,
          "paired_median_reduction_pct": 30.988023613196724,
          "reduction_from_total_time_pct": 31.159382738181552,
          "all_bytes_equal": true
        },
        "len128_129": {
          "samples": 5,
          "baseline_median_ms": 8817.573043052107,
          "candidate_median_ms": 6236.592689994723,
          "reduction_from_medians_pct": 29.270870118746483,
          "paired_median_reduction_pct": 29.109589246300494,
          "reduction_from_total_time_pct": 29.31022220781434,
          "all_bytes_equal": true
        },
        "len257_7": {
          "samples": 5,
          "baseline_median_ms": 8573.759375140071,
          "candidate_median_ms": 5901.743309106678,
          "reduction_from_medians_pct": 31.165046149778842,
          "paired_median_reduction_pct": 31.173461850436233,
          "reduction_from_total_time_pct": 31.387062448337776,
          "all_bytes_equal": true
        }
      }
    }
  },
  "pairs_count": 20,
  "rows_count": 48
}
```

## 034. formal-shapes-v4-window0

开始UTC：2026-10-23T22:24:23.849695+00:00；澳门：2026-10-24T06:24:23+08:00；结束UTC：2026-10-23T22:29:51.558764+00:00。

退出码：0；外来GPU干扰：False；profile：none。

实际命令、身份、遥测、日志：[run.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/formal-shapes-v4-window0/run.json)；Workflow start event：evt-20261023T222421532104Z-986ae31018。

证据：[本次paired-full-port-e2e.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/formal-shapes-v4-window0/paired-full-port-e2e.json)

```json
{
  "complete": true,
  "gate_passed": true,
  "summary": {
    "0": {
      "samples": 21,
      "baseline_median_ms": 4255.298003088683,
      "candidate_median_ms": 2947.480079019442,
      "reduction_from_medians_pct": 30.73387394067275,
      "paired_median_reduction_pct": 30.73387394067275,
      "reduction_from_total_time_pct": 31.566326641589416,
      "all_bytes_equal": true,
      "by_case": {
        "video320x512": {
          "samples": 7,
          "baseline_median_ms": 3283.4424960892648,
          "candidate_median_ms": 2291.5985269937664,
          "reduction_from_medians_pct": 30.20744143614,
          "paired_median_reduction_pct": 28.91326559117351,
          "reduction_from_total_time_pct": 28.899428765089365,
          "all_bytes_equal": true
        },
        "video17frames": {
          "samples": 7,
          "baseline_median_ms": 4255.298003088683,
          "candidate_median_ms": 2947.480079019442,
          "reduction_from_medians_pct": 30.73387394067275,
          "paired_median_reduction_pct": 30.73387394067275,
          "reduction_from_total_time_pct": 30.749931000527297,
          "all_bytes_equal": true
        },
        "action16": {
          "samples": 7,
          "baseline_median_ms": 8696.333406958729,
          "candidate_median_ms": 5811.11081992276,
          "reduction_from_medians_pct": 33.17746056892482,
          "paired_median_reduction_pct": 32.3092558610391,
          "reduction_from_total_time_pct": 32.99956368253294,
          "all_bytes_equal": true
        }
      }
    }
  },
  "pairs_count": 21,
  "rows_count": 50
}
```

## 035. formal-shapes-v4-window1

开始UTC：2026-10-23T22:29:54.181248+00:00；澳门：2026-10-24T06:29:54+08:00；结束UTC：2026-10-23T22:35:22.110711+00:00。

退出码：0；外来GPU干扰：False；profile：none。

实际命令、身份、遥测、日志：[run.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/formal-shapes-v4-window1/run.json)；Workflow start event：evt-20261023T222951895584Z-98f6281208。

证据：[本次paired-full-port-e2e.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/formal-shapes-v4-window1/paired-full-port-e2e.json)

```json
{
  "complete": true,
  "gate_passed": true,
  "summary": {
    "1": {
      "samples": 21,
      "baseline_median_ms": 4183.037859853357,
      "candidate_median_ms": 2947.198434965685,
      "reduction_from_medians_pct": 29.54406501429553,
      "paired_median_reduction_pct": 31.21197205407047,
      "reduction_from_total_time_pct": 31.035620114595574,
      "all_bytes_equal": true,
      "by_case": {
        "video320x512": {
          "samples": 7,
          "baseline_median_ms": 3310.546330176294,
          "candidate_median_ms": 2296.6966109815985,
          "reduction_from_medians_pct": 30.624846115375338,
          "paired_median_reduction_pct": 28.01769784083681,
          "reduction_from_total_time_pct": 28.297252823779083,
          "all_bytes_equal": true
        },
        "video17frames": {
          "samples": 7,
          "baseline_median_ms": 4183.037859853357,
          "candidate_median_ms": 2947.198434965685,
          "reduction_from_medians_pct": 29.54406501429553,
          "paired_median_reduction_pct": 29.36896815946589,
          "reduction_from_total_time_pct": 29.725278817738044,
          "all_bytes_equal": true
        },
        "action16": {
          "samples": 7,
          "baseline_median_ms": 8689.239487051964,
          "candidate_median_ms": 5814.565205015242,
          "reduction_from_medians_pct": 33.08315171103685,
          "paired_median_reduction_pct": 32.96791649707582,
          "reduction_from_total_time_pct": 32.731150354137064,
          "all_bytes_equal": true
        }
      }
    }
  },
  "pairs_count": 21,
  "rows_count": 50
}
```

## 036. graph-fallback-full-port-v4

开始UTC：2026-10-23T22:35:24.743787+00:00；澳门：2026-10-24T06:35:24+08:00；结束UTC：2026-10-23T22:36:08.746740+00:00。

退出码：0；外来GPU干扰：False；profile：none。

实际命令、身份、遥测、日志：[run.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/graph-fallback-full-port-v4/run.json)；Workflow start event：evt-20261023T223522439068Z-9d4c5ed66f。

证据：[本次graph-fallback-validation.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/graph-fallback-full-port-v4/graph-fallback-validation.json)

```json
{
  "complete": true,
  "gate_passed": true,
  "rows_count": 4
}
```

## 037. profile-main-full-port-v4

开始UTC：2026-10-23T22:36:11.348785+00:00；澳门：2026-10-24T06:36:11+08:00；结束UTC：2026-10-23T22:37:09.374842+00:00。

退出码：0；外来GPU干扰：False；profile：none。

实际命令、身份、遥测、日志：[run.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/profile-main-full-port-v4/run.json)；Workflow start event：evt-20261023T223609041809Z-85c6862cf6。

证据：[本次profile-metadata.json](https://github.com/crycryout/ThorKDAWorkflow/blob/e52fa0107a4966712c4e8a2387150bb2e5b35dba/examples/cosmos3-nano-bf16-dynamic-full-port-20261024/results/profile-main-full-port-v4/profile-metadata.json)

```json
{
  "complete": true,
  "byte_equal": true
}
```

