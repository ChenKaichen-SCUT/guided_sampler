"""Explicit ablations: mode, phase budget, model exchange, CCSS on/off."""
PROFILES={
    'base_budget':{'ESG_MODE':'observe','ESG_CCSS_MS':'100'},
    'base_complete':{'ESG_MODE':'observe','ESG_CCSS_MS':'100','ESG_CCSS_FEEDBACK':'complete'},
    'base_off':{'ESG_MODE':'observe','ESG_CCSS_OFF':'1'},
    'soft_budget':{'ESG_MODE':'soft','ESG_CCSS_MS':'100'},
    'soft_complete':{'ESG_MODE':'soft','ESG_CCSS_MS':'100','ESG_CCSS_FEEDBACK':'complete'},
    'soft_hold':{'ESG_MODE':'soft','ESG_CCSS_MS':'100','ESG_CCSS_FEEDBACK':'hold'},
    'soft_off':{'ESG_MODE':'soft','ESG_CCSS_OFF':'1'},
    'soft_25':{'ESG_MODE':'soft','ESG_CCSS_MS':'25'},
    'soft_500':{'ESG_MODE':'soft','ESG_CCSS_MS':'500'},
}
