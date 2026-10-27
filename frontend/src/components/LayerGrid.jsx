import React, { useState } from 'react';
import { UserCheck, Key, FileText, Server, GitCommit, ChevronDown, ChevronUp, CheckCircle, AlertCircle, HelpCircle } from 'lucide-react';

export default function LayerGrid({ layer1, layer2, layer3, layer4, layer5 }) {
  const [expandedLayer, setExpandedLayer] = useState(null);

  const toggleExpand = (layerId) => {
    setExpandedLayer(expandedLayer === layerId ? null : layerId);
  };

  const getStatusBadge = (status) => {
    if (status === 'VERIFIED') {
      return (
        <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-emerald-950 text-emerald-400 border border-emerald-800">
          <CheckCircle className="w-3 h-3 text-emerald-400" />
          <span>VERIFIED</span>
        </span>
      );
    } else if (status === 'PROBABLE') {
      return (
        <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-amber-950 text-amber-400 border border-amber-800">
          <HelpCircle className="w-3 h-3 text-amber-400" />
          <span>PROBABLE</span>
        </span>
      );
    } else {
      return (
        <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-rose-950 text-rose-400 border border-rose-800">
          <AlertCircle className="w-3 h-3 text-rose-400" />
          <span>UNCERTAIN</span>
        </span>
      );
    }
  };

  const layers = [
    {
      id: 'layer1',
      num: 'LAYER 1',
      title: 'Claimed Identity',
      icon: <UserCheck className="w-5 h-5 text-cyan-400" />,
      status: layer1?.status || 'UNCERTAIN',
      summary: layer1?.summary || 'N/A',
      subtitle: 'From, Reply-To, Signature parsing',
      details: [
        { label: 'Claimed Role', value: layer1?.claimed_role || 'None Extracted' },
        { label: 'Claimed Org', value: layer1?.claimed_org || 'None Extracted' },
        { label: 'Claimed Location', value: layer1?.claimed_location_full || 'None Specified' },
        { label: 'From Address', value: layer1?.from_address || 'N/A' },
        { label: 'Reply-To Address', value: layer1?.reply_to_address || 'N/A' }
      ]
    },
    {
      id: 'layer2',
      num: 'LAYER 2',
      title: 'Technical Identity',
      icon: <Key className="w-5 h-5 text-blue-400" />,
      status: layer2?.status || 'UNCERTAIN',
      summary: layer2?.summary || 'N/A',
      subtitle: 'SPF, DKIM, DMARC alignment check',
      details: [
        { label: 'SPF Result', value: (layer2?.spf_result || 'none').toUpperCase() },
        { label: 'DKIM Result', value: (layer2?.dkim_result || 'none').toUpperCase() },
        { label: 'DKIM Signing Domain', value: layer2?.dkim_signing_domain || 'None' },
        { label: 'DMARC Result', value: (layer2?.dmarc_result || 'none').toUpperCase() },
        { label: 'Domain Alignment', value: layer2?.domain_aligned ? 'ALIGNED (True)' : 'MISALIGNED (False)' }
      ]
    },
    {
      id: 'layer3',
      num: 'LAYER 3',
      title: 'Content & Intent',
      icon: <FileText className="w-5 h-5 text-purple-400" />,
      status: layer3?.status || 'UNCERTAIN',
      summary: layer3?.summary || 'N/A',
      subtitle: 'Baseline classifier — trained on public + synthetic samples',
      badgeExtra: 'Baseline ML Classifier',
      details: [
        { label: 'Classification', value: (layer3?.classification || 'legitimate').toUpperCase() },
        { label: 'Triggering Cues', value: layer3?.triggering_phrases?.length ? layer3.triggering_phrases.join(', ') : 'None' },
        { label: 'Model Info', value: layer3?.model_type || 'TF-IDF + Logistic Regression' }
      ]
    },
    {
      id: 'layer4',
      num: 'LAYER 4',
      title: 'Infrastructure',
      icon: <Server className="w-5 h-5 text-emerald-400" />,
      status: layer4?.status || 'UNCERTAIN',
      summary: layer4?.summary || 'N/A',
      details: [
        { 
          label: 'Originating IP', 
          value: layer4?.originating_ip || 'No origin IP' 
        },
        { 
          label: 'Geolocated Region', 
          value: !layer4?.is_resolved || !layer4?.originating_ip 
            ? 'Unresolved' 
            : `${layer4?.city || 'Unknown'}, ${layer4?.country || 'Unknown'}${layer4?.accuracy_radius_km ? ` (±${layer4.accuracy_radius_km} km radius)` : ''}` 
        },
        { 
          label: 'ASN & Provider', 
          value: layer4?.asn ? `${layer4?.asn} (${layer4?.asn_org || 'Unknown'})` : 'Unresolved' 
        },
        { 
          label: 'Infra Category', 
          value: (layer4?.infra_category || 'no_origin_ip').toUpperCase() 
        },
        { 
          label: 'Domain Age', 
          value: layer4?.domain_age_days == null 
            ? 'Unknown' 
            : `${layer4.domain_age_days} days (${layer4?.registrar || 'Registrar'})` 
        }
      ]
    },
    {
      id: 'layer5',
      num: 'LAYER 5',
      title: 'Historical Pattern',
      icon: <GitCommit className="w-5 h-5 text-amber-400" />,
      status: layer5?.status || 'UNCERTAIN',
      summary: layer5?.summary || 'N/A',
      subtitle: 'NetworkX graph match vs 30-case dataset',
      details: [
        { label: 'Cluster Match', value: layer5?.cluster_match ? 'MATCH FOUND (True)' : 'No Prior Cluster (False)' },
        { label: 'Matched Case IDs', value: layer5?.matched_case_ids?.length ? layer5.matched_case_ids.join(', ') : 'None' },
        { label: 'Graph Subgraph Nodes', value: `${layer5?.subgraph_nodes?.length || 0} Nodes Connected` }
      ]
    }
  ];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-base font-bold text-white">5-Layer Forensic Evidence Engine</h3>
        <span className="text-xs text-slate-400 font-mono">Independent Status Badges (Never Blended)</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        {layers.map((layer) => {
          const isExpanded = expandedLayer === layer.id;
          return (
            <div
              key={layer.id}
              className="bg-[#111827] border border-slate-800 hover:border-slate-700 rounded-xl p-4 transition-all flex flex-col justify-between space-y-3"
            >
              {/* Header */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono font-bold text-cyan-400 tracking-wider">
                    {layer.num}
                  </span>
                  {getStatusBadge(layer.status)}
                </div>

                {layer.id === 'layer4' && (
                  <div className="pt-0.5">
                    <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-800">
                      {layer4?.geoip_source === 'real_database' ? 'Real GeoIP database (DB-IP Lite)' : 'Simulated demo dataset'}
                    </span>
                  </div>
                )}

                <div className="flex items-center space-x-2 pt-1">
                  {layer.icon}
                  <h4 className="text-sm font-bold text-white line-clamp-1">{layer.title}</h4>
                </div>

                <p className="text-[11px] text-slate-400 line-clamp-2 leading-relaxed">
                  {layer.summary}
                </p>
              </div>

              {/* Accordion Toggle */}
              <div className="border-t border-slate-800/80 pt-2">
                <button
                  onClick={() => toggleExpand(layer.id)}
                  className="w-full flex items-center justify-between text-[11px] font-medium text-slate-400 hover:text-cyan-300 transition-colors"
                >
                  <span>{isExpanded ? 'Hide Technical Details' : 'Inspect Layer Data'}</span>
                  {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                </button>

                {isExpanded && (
                  <div className="mt-3 space-y-2 text-[11px] font-mono bg-slate-900/80 p-3 rounded-lg border border-slate-800">
                    {layer.details.map((d, idx) => (
                      <div key={idx} className="flex justify-between border-b border-slate-800/50 pb-1 last:border-b-0">
                        <span className="text-slate-500">{d.label}:</span>
                        <span className="text-slate-200 font-semibold text-right max-w-[120px] truncate" title={d.value}>
                          {d.value}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

            </div>
          );
        })}
      </div>
    </div>
  );
}
