#!/bin/bash

COLLECTION="summaries"
SOLR_HOST="https://solr.dev.dgfisma.crosslang.com"

JSON='{"add-field": [
{"name":"title",            "type":"text_general","stored":true,"indexed":true,"multiValued":true},
{"name":"url"               "type":"text_general","stored":true,"indexed":true,"multiValued":true},
{"name":"celex",            "type":"text_general","stored":true,"indexed":true,"multiValued":true},
{"name":"html_content",     "type":"text_general","stored":true,"indexed":true,"multiValued":true},
{"name":"pull",             "type":"boolean","stored":true,"indexed":true,"multiValued":true},

{"name":"classifications",          "type":"text_general","stored":true,"indexed":true,"multiValued":true},
{"name":"classifications_code",     "type":"text_general","stored":true,"indexed":true,"multiValued":true},
{"name":"classifications_label",    "type":"text_general","stored":true,"indexed":true,"multiValued":true},
{"name":"classifications_type",     "type":"text_general","stored":true,"indexed":true,"multiValued":true},

{"name":"dates",                    "type":"pdates","stored":true,"indexed":true,"multiValued":true},
{"name":"dates_info",               "type":"text_general","stored":true,"indexed":true,"multiValued":true},
{"name":"dates_type",               "type":"text_general","stored":true,"indexed":true,"multiValued":true},

{"name":"created_at",               "type":"pdates","stored":true,"indexed":true,"multiValued":true},
{"name":"updated_at",               "type":"pdates","stored":true,"indexed":true,"multiValued":true},

{"name":"spider",          "type":"text_general","stored":true,"indexed":true,"multiValued":true},
{"name":"task",            "type":"plongs","stored":true,"indexed":true,"multiValued":true},
]
}';

JSON_DYNAMIC_FIELDS='{"add-dynamic-field": [
{"name":"misc_*", "type":"text_general", "stored":true, "indexed":true, "multiValued":true},
]
}'

curl -k -X POST --user crosslang: pass -H 'Content-type:application/json' --data-binary "$JSON" $SOLR_HOST/solr/$COLLECTION/schema
curl -k -X POST --user crosslang: pass -H 'Content-type:application/json' --data-binary "$JSON_DYNAMIC_FIELDS" $SOLR_HOST/solr/$COLLECTION/schema
curl -k $SOLR_HOST/solr/$COLLECTION/config -d '{"set-user-property": {"update.autoCreateFields":"false"}}'
