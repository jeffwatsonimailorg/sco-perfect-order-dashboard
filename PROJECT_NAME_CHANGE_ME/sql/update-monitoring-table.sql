USE CATALOG {{catalog}};
USE IDENTIFIER({{schema}});

MERGE INTO PROJECT_NAME_CHANGE_ME_inference AS target
USING (
  with all_icds as (
    SELECT
      rawdx.HSP_ACCOUNT_ID,
      ARRAY_JOIN(
        TRANSFORM(
          ARRAY_SORT(
            ARRAY_AGG( (rawdx.CURRENT_ICD10_LIST, rawdx.LINE) ), (left, right) -> CASE WHEN left.line < right.line THEN -1 WHEN left.line > right.line THEN 1 ELSE 0 END
                    ), x -> x.CURRENT_ICD10_LIST
                ), '; '
              ) as ICD10_DX
    FROM
      (SELECT DISTINCT
        fdx.HSP_ACCOUNT_ID,
        fdx.LINE,
        fdx.DX_ID, 
        dx.CURRENT_ICD10_LIST
      FROM prod_bronze.emr.epic_hsp_acct_dx_list_t fdx 
      left join prod_bronze.emr.epic_clarity_edg_t dx on fdx.DX_ID = dx.DX_ID
      order by fdx.HSP_ACCOUNT_ID, fdx.LINE) rawdx
      WHERE 1=1 
    GROUP BY rawdx.HSP_ACCOUNT_ID
  )
  , grouped_icds as (
    select 
      hsp_account_id,
      split_part(icd10_dx, '; ', 1) || '; ' || split_part(icd10_dx, '; ', 2) as first_two_icd10_dx,
      substring(icd10_dx, length(split_part(icd10_dx, '; ', 1) || '; ' || split_part(icd10_dx, '; ', 2)) + 3) as remaining_icd10_dx,
      icd10_dx
    from all_icds
  )
  , truth as (
    select 
      enc.PAT_ENC_CSN_ID,
      -- first_two_icd10_dx,
      -- remaining_icd10_dx,
      max(1) as pneumonia_truth
    from grouped_icds p
    left join prod_silver.emr.epic_pat_enc enc
      on p.HSP_ACCOUNT_ID = enc.HSP_ACCOUNT_ID
      and enc.PAT_ENC_CSN_ID is not null
    where (
        first_two_icd10_dx like '%A48.1%'
        or first_two_icd10_dx like '%B01.2%'
        or first_two_icd10_dx like '%J10.0%'
        or first_two_icd10_dx like '%J11.0%'
        or first_two_icd10_dx like '%J85.1%'
        or first_two_icd10_dx rlike 'J1(2|3|4|5|6|8)'
      )
      or (
        (
          /* sepsis */
          first_two_icd10_dx rlike 'A4(0|1)'
          or first_two_icd10_dx like '%R78.81%'
          or first_two_icd10_dx like '%R65.20%'
          or first_two_icd10_dx like '%R65.21%'
          /* respiratory failure */
          or first_two_icd10_dx rlike 'J96\.(0|2|6)'
          or first_two_icd10_dx like '%J80%'
        )
        and (
          remaining_icd10_dx like '%A48.1%'
          or remaining_icd10_dx like '%B01.2%'
          or remaining_icd10_dx like '%J10.0%'
          or remaining_icd10_dx like '%J11.0%'
          or remaining_icd10_dx like '%J85.1%'
          or remaining_icd10_dx rlike 'J1(2|3|4|5|6|8)'
        )
      )
    group by all
  )
  , result as (
    select
      sc.PAT_ENC_CSN_ID,
      sc.PAT_ID,
      floor(datediff(sc.SCORE_FILE_LOC_DTTM, pt.birth_date) / 365.25) as age,
      sl.NAME as sex,
      el.NAME as ethnic_group,
      ms.NAME as marital_status,
      rl.NAME as religion,
      ll.NAME as language,
      sc.TOTAL_SCORE/100 as pred_score,
      cast(
        case when sc.TOTAL_SCORE > 50 then 1 --high risk
            when sc.TOTAL_SCORE > 10 then 0 --medium risk
            else 0
        end as int
      ) as pred_class,
      sc.ACUITY_SYSTEM_ID AS model_id,
      sc.ACUITY_SYSTEM_CSN_ID AS model_csn_id,
      upper(sc.ADV_MODEL_SELECTED) as model_name,
      sc.MODEL_VERSION_C AS model_version,
      sc.SCORE_FILE_LOC_DTTM as prediction_dts,
      cast(nvl(tr.pneumonia_truth, 0) as int) as pneumonia_truth,
      from_utc_timestamp(current_timestamp(),'US/Mountain') as edp_load_dts,
      row_number() over (partition by sc.PAT_ENC_CSN_ID order by sc.line desc) as rn
    from prod_bronze.emr.epic_v_predictive_model_scores_t sc 
    left join prod_silver.emr.epic_patient pt
      on sc.PAT_ID = pt.PAT_ID
    left join prod_silver.emr_epic.epic_zc_sex sl
      on pt.sex_c = sl.RCPT_MEM_SEX_C
    left join prod_silver.emr_epic.epic_zc_ethnic_group el
      on pt.ETHNIC_GROUP_C = el.ETHNIC_GROUP_C
    left join prod_silver.emr_epic.epic_zc_marital_status ms
      on pt.MARITAL_STATUS_C = ms.MARITAL_STATUS_C
    left join prod_silver.emr_epic.epic_zc_religion rl
      on pt.RELIGION_C = rl.RELIGION_C
    left join prod_silver.emr_epic.epic_zc_language ll
      on pt.LANGUAGE_C = ll.LANGUAGE_C
    left join truth tr
      on sc.PAT_ENC_CSN_ID = tr.PAT_ENC_CSN_ID
    where 1=1
      and sc.ACUITY_SYSTEM_ID in (100044)
      and sc.CONTACT_DATE >= dateadd(month, -1, current_date())
  )
  select 
      PAT_ENC_CSN_ID,
      PAT_ID,
      age,
      sex,
      ethnic_group,
      marital_status,
      religion,
      language,
      pred_score,
      pred_class,
      model_id,
      model_csn_id,
      model_name,
      model_version,
      prediction_dts,
      pneumonia_truth,
      edp_load_dts
  from result
  where rn = 1
) AS source
ON target.PAT_ENC_CSN_ID = source.PAT_ENC_CSN_ID
and target.prediction_dts = source.prediction_dts
WHEN MATCHED AND (
    target.PAT_ID <> source.PAT_ID OR
    target.age <> source.age OR
    target.sex <> source.sex OR
    target.ethnic_group <> source.ethnic_group OR
    target.marital_status <> source.marital_status OR
    target.religion <> source.religion OR
    target.language <> source.language OR
    target.pred_score <> source.pred_score OR
    target.pred_class <> source.pred_class OR
    target.model_id <> source.model_id OR
    target.model_csn_id <> source.model_csn_id OR
    target.model_name <> source.model_name OR
    target.model_version <> source.model_version OR
    target.prediction_dts <> source.prediction_dts OR
    target.pneumonia_truth <> source.pneumonia_truth
) THEN UPDATE SET
  PAT_ID = source.PAT_ID,
  age = source.age,
  sex = source.sex,
  ethnic_group = source.ethnic_group,
  marital_status = source.marital_status,
  religion = source.religion,
  language = source.language,
  pred_score = source.pred_score,
  pred_class = source.pred_class,
  model_id = source.model_id,
  model_csn_id = source.model_csn_id,
  model_name = source.model_name,
  model_version = source.model_version,
  prediction_dts = source.prediction_dts,
  pneumonia_truth = source.pneumonia_truth,
  edp_load_dts = source.edp_load_dts
WHEN NOT MATCHED THEN INSERT (
  PAT_ENC_CSN_ID,
  PAT_ID,
  age,
  sex,
  ethnic_group,
  marital_status,
  religion,
  language,
  pred_score,
  pred_class,
  model_id,
  model_csn_id,
  model_name,
  model_version,
  prediction_dts,
  pneumonia_truth,
  edp_load_dts
) VALUES (
  source.PAT_ENC_CSN_ID,
  source.PAT_ID,
  source.age,
  source.sex,
  source.ethnic_group,
  source.marital_status,
  source.religion,
  source.language,
  source.pred_score,
  source.pred_class,
  source.model_id,
  source.model_csn_id,
  source.model_name,
  source.model_version,
  source.prediction_dts,
  source.pneumonia_truth,
  source.edp_load_dts
);