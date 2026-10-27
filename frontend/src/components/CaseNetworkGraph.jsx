import React, { useEffect, useRef, useState } from 'react';
import { Network, GitBranch, ShieldCheck, ShieldAlert, Sparkles } from 'lucide-react';

export default function CaseNetworkGraph({ layer5 }) {
  const containerRef = useRef(null);

  const nodes = layer5?.subgraph_nodes || [];
  const edges = layer5?.subgraph_edges || [];
  const clusterMatch = layer5?.cluster_match;
  const matchedCaseIds = layer5?.matched_case_ids || [];
  const hasFraudMatch = layer5?.details?.has_fraud_match;

  const [hoveredNode, setHoveredNode] = useState(null);

  // Pure SVG/Canvas interactive force layout calculation for guaranteed 100% rendering reliability
  const [layoutNodes, setLayoutNodes] = useState([]);

  useEffect(() => {
    if (!nodes || nodes.length === 0) {
      // Fallback default node if somehow empty
      setLayoutNodes([{
        id: "CURRENT_EMAIL",
        label: "Submitted Email (Isolated — No Cluster Match)",
        type: "current_email",
        x: 250,
        y: 100
      }]);
      return;
    }

    if (nodes.length === 1) {
      // Single isolated node center layout
      setLayoutNodes([{
        ...nodes[0],
        x: 250,
        y: 100
      }]);
      return;
    }

    // Radial layout around center node for multi-node graph
    const width = 500;
    const height = 220;
    const centerX = width / 2;
    const centerY = height / 2;
    const radius = 85;

    const centerNode = nodes.find(n => n.type === 'current_email') || nodes[0];
    const outerNodes = nodes.filter(n => n.id !== centerNode.id);

    const calculated = [
      { ...centerNode, x: centerX, y: centerY }
    ];

    outerNodes.forEach((node, idx) => {
      const angle = (idx / outerNodes.length) * 2 * Math.PI - Math.PI / 2;
      calculated.push({
        ...node,
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle)
      });
    });

    setLayoutNodes(calculated);
  }, [nodes]);

  const getNodeColor = (type, status) => {
    if (type === 'current_email') return { bg: '#06B6D4', border: '#22D3EE', text: '#CFFAFE' };
    if (type === 'historical_case') {
      return status === 'CONFIRMED_FRAUD'
        ? { bg: '#F43F5E', border: '#FDA4AF', text: '#FFE4E6' }
        : { bg: '#10B981', border: '#6EE7B7', text: '#D1FAE5' };
    }
    if (type === 'indicator_ip') return { bg: '#8B5CF6', border: '#C4B5FD', text: '#EDE9FE' };
    if (type === 'indicator_domain') return { bg: '#F59E0B', border: '#FDE68A', text: '#FEF3C7' };
    return { bg: '#3B82F6', border: '#93C5FD', text: '#DBEAFE' };
  };

  return (
    <div className="bg-[#111827] border border-slate-800 rounded-2xl p-6 space-y-4 shadow-xl">
      
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center space-x-2.5">
          <Network className="w-5 h-5 text-amber-400" />
          <div>
            <h3 className="text-sm font-bold text-white">NetworkX Historical Correlation Graph</h3>
            <p className="text-[11px] text-slate-400">Maps shared indicators across past incident database</p>
          </div>
        </div>

        <div>
          {hasFraudMatch ? (
            <span className="text-xs font-mono font-bold px-2.5 py-1 rounded bg-rose-950 text-rose-400 border border-rose-800">
              FRAUD CLUSTER MATCH: {matchedCaseIds.join(', ')}
            </span>
          ) : clusterMatch ? (
            <span className="text-xs font-mono font-bold px-2.5 py-1 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">
              LEGITIMATE CLUSTER MATCH: {matchedCaseIds.join(', ')}
            </span>
          ) : (
            <span className="text-xs font-mono font-bold px-2.5 py-1 rounded bg-slate-900 text-cyan-400 border border-cyan-800">
              ISOLATED NODE (0 CLUSTER MATCHES)
            </span>
          )}
        </div>
      </div>

      {/* SVG Interactive Canvas */}
      <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 min-h-[220px] relative overflow-hidden flex flex-col justify-between">
        
        <svg viewBox="0 0 500 220" className="w-full h-[200px] overflow-visible">
          <defs>
            <filter id="glow-cyan" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
            <filter id="glow-rose" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="4" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
          </defs>

          {/* Render Edges */}
          {edges.map((edge, idx) => {
            const sourceNode = layoutNodes.find(n => n.id === edge.source);
            const targetNode = layoutNodes.find(n => n.id === edge.target);

            if (!sourceNode || !targetNode) return null;

            const midX = (sourceNode.x + targetNode.x) / 2;
            const midY = (sourceNode.y + targetNode.y) / 2;

            return (
              <g key={idx}>
                <line
                  x1={sourceNode.x}
                  y1={sourceNode.y}
                  x2={targetNode.x}
                  y2={targetNode.y}
                  stroke="#334155"
                  strokeWidth="1.5"
                  strokeDasharray={edge.relationship?.includes('Shared') ? '4' : 'none'}
                />
                <rect
                  x={midX - 30}
                  y={midY - 8}
                  width="60"
                  height="14"
                  rx="3"
                  fill="#0F172A"
                  stroke="#1E293B"
                  strokeWidth="0.5"
                />
                <text
                  x={midX}
                  y={midY + 2}
                  textAnchor="middle"
                  fill="#94A3B8"
                  fontSize="8"
                  fontFamily="JetBrains Mono, monospace"
                  fontWeight="bold"
                >
                  {edge.relationship || 'linked'}
                </text>
              </g>
            );
          })}

          {/* Render Nodes */}
          {layoutNodes.map((node) => {
            const colors = getNodeColor(node.type, node.status);
            const isCenter = node.type === 'current_email';
            const isHovered = hoveredNode === node.id;

            return (
              <g
                key={node.id}
                transform={`translate(${node.x}, ${node.y})`}
                onMouseEnter={() => setHoveredNode(node.id)}
                onMouseLeave={() => setHoveredNode(null)}
                className="cursor-pointer transition-transform duration-200"
              >
                {/* Node Outer Ring */}
                {isCenter && !clusterMatch && (
                  <circle
                    r="24"
                    fill="none"
                    stroke="#06B6D4"
                    strokeWidth="1.5"
                    strokeDasharray="3 3"
                    className="animate-spin"
                    style={{ animationDuration: '10s' }}
                  />
                )}

                {/* Node Main Circle */}
                <circle
                  r={isCenter ? 16 : 12}
                  fill={colors.bg}
                  stroke={colors.border}
                  strokeWidth={isHovered ? 3 : 1.5}
                  filter={isCenter ? (hasFraudMatch ? 'url(#glow-rose)' : 'url(#glow-cyan)') : 'none'}
                />

                {/* Node Center Symbol */}
                <text
                  x="0"
                  y="4"
                  textAnchor="middle"
                  fill="#FFFFFF"
                  fontSize={isCenter ? '11' : '9'}
                  fontWeight="bold"
                  fontFamily="JetBrains Mono, monospace"
                >
                  {node.type === 'current_email' ? '★' : (node.type === 'historical_case' ? '◆' : '●')}
                </text>

                {/* Node Label Text */}
                <text
                  x="0"
                  y={isCenter ? 32 : 24}
                  textAnchor="middle"
                  fill={colors.text}
                  fontSize="9"
                  fontWeight="600"
                  fontFamily="JetBrains Mono, monospace"
                  className="drop-shadow-md"
                >
                  {node.label.length > 35 ? `${node.label.substring(0, 32)}...` : node.label}
                </text>
              </g>
            );
          })}

        </svg>

        {/* Node Legend Bar */}
        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-900 pt-3 text-[11px] font-mono text-slate-400">
          <div className="flex flex-wrap items-center gap-3">
            <span className="flex items-center space-x-1">
              <span className="w-2.5 h-2.5 rounded-full bg-cyan-400"></span>
              <span>Submitted Email</span>
            </span>
            <span className="flex items-center space-x-1">
              <span className="w-2.5 h-2.5 rounded-full bg-rose-500"></span>
              <span>Prior Fraud Case</span>
            </span>
            <span className="flex items-center space-x-1">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400"></span>
              <span>Clean Prior Case</span>
            </span>
            <span className="flex items-center space-x-1">
              <span className="w-2.5 h-2.5 rounded-full bg-purple-400"></span>
              <span>Shared IP</span>
            </span>
            <span className="flex items-center space-x-1">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-400"></span>
              <span>Shared Domain</span>
            </span>
          </div>

          <span className="text-[10px] text-slate-500">
            {clusterMatch ? `${layoutNodes.length} Graph Nodes Rendered` : 'Single Node (Isolated)'}
          </span>
        </div>

      </div>

    </div>
  );
}
