USE CATALOG {{catalog}};
USE IDENTIFIER({{schema}});

create table if not exists PROJECT_NAME_CHANGE_ME_inference as
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
    -- ml.NAME as model_version,
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
  -- left join prod_silver.emr_epic.epic_zc_model_version ml
  --   on sc.MODEL_VERSION_C = ml.MODEL_VERSION_C
  left join truth tr
    on sc.PAT_ENC_CSN_ID = tr.PAT_ENC_CSN_ID
  where 1=1
    and sc.ACUITY_SYSTEM_ID in (100044)
    and sc.CONTACT_DATE >= '2025-05-01'
    and sc.CONTACT_DATE <= dateadd(month, -1, current_date())
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
where rn = 1;
  
GRANT MANAGE ON TABLE PROJECT_NAME_CHANGE_ME_inference TO DP_DAP_MLOPS_USR;

--enable change data capture
ALTER TABLE PROJECT_NAME_CHANGE_ME_inference SET TBLPROPERTIES (delta.enableChangeDataFeed = true);
