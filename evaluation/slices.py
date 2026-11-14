"""Development-defined descriptive slices, without subgroup selection."""
from hardcase.mining.retrieval import words
from .metrics import qrel_map
from .statistics import quantile


def overlap(query, relevant, documents):
    query_terms=set(words(query))
    values=[]
    for document_id,score in relevant.items():
        if score>0:
            terms=set(words(documents[document_id]['visible_text']))
            values.append(len(query_terms & terms)/len(query_terms | terms) if query_terms | terms else 0.0)
    return max(values) if values else None


def boundaries(train_queries, fit_ids, train_labels, documents):
    gold=qrel_map(train_labels)
    lengths=[len(train_queries[q]['text']) for q in fit_ids]
    overlaps=[overlap(train_queries[q]['text'],gold[q],documents) for q in fit_ids]
    return {'query_length_characters':[quantile(lengths,p) for p in (1/3,2/3)],'max_relevant_token_jaccard':[quantile(overlaps,p) for p in (1/3,2/3)],'boundary_source':'fit queries and fit relevance labels only','definitions':'Unicode character length; maximum word-set Jaccard with a known relevant visible document; fixed tertiles; one/multiple relevant; any known relevant document truncated'}


def describe(queries,labels,documents,bins,metric_rows):
    gold=qrel_map(labels)
    properties=[]
    for q in sorted(queries):
        text=queries[q]['text']
        lexical=overlap(text,gold[q],documents)
        properties.append({'query_id':q,'query_length_characters':len(text),'length_bin':sum(len(text)>b for b in bins['query_length_characters']),'max_relevant_token_jaccard':lexical,'lexical_overlap_bin':sum(lexical>b for b in bins['max_relevant_token_jaccard']) if lexical is not None else None,'relevant_count_bin':'one' if sum(s>0 for s in gold[q].values())==1 else 'multiple','any_relevant_truncated':any(documents[d].get('truncated',False) for d,s in gold[q].items() if s>0)})
    rows_by_query={r['query_id']:r for r in properties}
    summaries=[]
    for field in ('length_bin','lexical_overlap_bin','relevant_count_bin','any_relevant_truncated'):
        for value in sorted({str(r[field]) for r in properties}):
            members={q for q,row in rows_by_query.items() if str(row[field])==value}
            for method in sorted({r['method'] for r in metric_rows}):
                complete=[r for r in metric_rows if r['method']==method and r['query_id'] in members and r['status']=='completed']
                summaries.append({'slice':field,'value':value,'method':method,'planned_queries':len(members),'completed_queries':len(complete),'mean_ndcg10':sum(r['metrics']['ndcg10'] for r in complete)/len(members) if len(complete)==len(members) else None,'interpretation':'descriptive only; small cells are not evidence of a stable subgroup effect'})
    return {'development_boundaries':bins,'rows':properties,'summaries':summaries,'interpretation':'Fixed source-property slices; no subgroup significance claim.'}
