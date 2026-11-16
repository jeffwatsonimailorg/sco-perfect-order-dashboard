-- Grant SELECT permissions for pneumonia inference data sources
-- Groups: DPG_SP_GH_DATA_MLOPS_EPNEUMONIA_TST and DPG_SP_GH_DATA_MLOPS_EPNEUMONIA_PRD

-- Grant permissions on bronze EMR tables
GRANT SELECT ON TABLE prod_bronze.emr.epic_hsp_acct_dx_list_t TO DPG_SP_GH_DATA_MLOPS_EPNEUMONIA_TST;
GRANT SELECT ON TABLE prod_bronze.emr.epic_hsp_acct_dx_list_t TO DPG_SP_GH_DATA_MLOPS_EPNEUMONIA_PRD;

GRANT SELECT ON TABLE prod_bronze.emr.epic_clarity_edg_t TO DPG_SP_GH_DATA_MLOPS_EPNEUMONIA_TST;
GRANT SELECT ON TABLE prod_bronze.emr.epic_clarity_edg_t TO DPG_SP_GH_DATA_MLOPS_EPNEUMONIA_PRD;

-- Grant permissions on silver EMR tables
GRANT SELECT ON TABLE prod_silver.emr.epic_pat_enc TO DPG_SP_GH_DATA_MLOPS_EPNEUMONIA_TST;
GRANT SELECT ON TABLE prod_silver.emr.epic_pat_enc TO DPG_SP_GH_DATA_MLOPS_EPNEUMONIA_PRD;

-- Grant permissions on additional tables used in the inference pipeline
GRANT SELECT ON TABLE prod_bronze.emr.epic_v_predictive_model_scores_t TO DPG_SP_GH_DATA_MLOPS_EPNEUMONIA_TST;
GRANT SELECT ON TABLE prod_bronze.emr.epic_v_predictive_model_scores_t TO DPG_SP_GH_DATA_MLOPS_EPNEUMONIA_PRD;

GRANT SELECT ON TABLE prod_silver.emr.epic_patient TO DPG_SP_GH_DATA_MLOPS_EPNEUMONIA_TST;
GRANT SELECT ON TABLE prod_silver.emr.epic_patient TO DPG_SP_GH_DATA_MLOPS_EPNEUMONIA_PRD;

GRANT SELECT ON TABLE prod_silver.emr_epic.epic_zc_sex TO DPG_SP_GH_DATA_MLOPS_EPNEUMONIA_TST;
GRANT SELECT ON TABLE prod_silver.emr_epic.epic_zc_sex TO DPG_SP_GH_DATA_MLOPS_EPNEUMONIA_PRD;

GRANT SELECT ON TABLE prod_silver.emr_epic.epic_zc_ethnic_group TO DPG_SP_GH_DATA_MLOPS_EPNEUMONIA_TST;
GRANT SELECT ON TABLE prod_silver.emr_epic.epic_zc_ethnic_group TO DPG_SP_GH_DATA_MLOPS_EPNEUMONIA_PRD;

GRANT SELECT ON TABLE prod_silver.emr_epic.epic_zc_marital_status TO DPG_SP_GH_DATA_MLOPS_EPNEUMONIA_TST;
GRANT SELECT ON TABLE prod_silver.emr_epic.epic_zc_marital_status TO DPG_SP_GH_DATA_MLOPS_EPNEUMONIA_PRD;

GRANT SELECT ON TABLE prod_silver.emr_epic.epic_zc_religion TO DPG_SP_GH_DATA_MLOPS_EPNEUMONIA_TST;
GRANT SELECT ON TABLE prod_silver.emr_epic.epic_zc_religion TO DPG_SP_GH_DATA_MLOPS_EPNEUMONIA_PRD;

GRANT SELECT ON TABLE prod_silver.emr_epic.epic_zc_language TO DPG_SP_GH_DATA_MLOPS_EPNEUMONIA_TST;
GRANT SELECT ON TABLE prod_silver.emr_epic.epic_zc_language TO DPG_SP_GH_DATA_MLOPS_EPNEUMONIA_PRD;
