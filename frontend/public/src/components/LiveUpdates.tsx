import { useState, useEffect } from 'react';
import pusherService from '../services/pusher';
import { bettingFormsAPI } from '../services/api';

export default function LiveUpdates({ formId }) {
  const [connected, setConnected] = useState(false);
  const [updates, setUpdates] = useState([]);
  const [games, setGames] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Fetch initial form data
    const loadFormData = async () => {
      try {
        const response = await bettingFormsAPI.getById(formId);
        console.log('Form data loaded:', response.data);
        setGames(response.data.games || []);
        setLoading(false);
      } catch (error) {
        console.error('Error loading form:', error);
        setLoading(false);
      }
    };

    loadFormData();

    // Connect to Pusher
    pusherService.connect(formId);

    // Set up event listeners
    pusherService.on('connection', (data) => {
      console.log('Connected:', data);
      setConnected(true);
    });

    pusherService.on('disconnection', (data) => {
      console.log('Disconnected:', data);
      setConnected(false);
    });

    pusherService.on('live-update', (data) => {
      console.log('Live update received:', data);
      
      // Add to updates list
      setUpdates((prev) => [data, ...prev].slice(0, 10));

      // Update games with new data
      if (data.updates) {
        setGames((prevGames) => {
          const updatedGames = [...prevGames];
          
          data.updates.forEach((update) => {
            const index = updatedGames.findIndex(
              (g) => g.game_id === update.game_id
            );
            
            if (index >= 0) {
              // Merge update with existing game data
              updatedGames[index] = {
                ...updatedGames[index],
                current_score: update.current_score,
                minute: update.minute,
                status: update.status,
                updated_prediction: update.updated_prediction,
                change: update.change
              };
            }
          });
          
          return updatedGames;
        });
      }
    });

    pusherService.on('notification', (data) => {
      console.log('Notification:', data.message);
    });

    pusherService.on('error', (data) => {
      console.error('Pusher error:', data);
    });

    // Cleanup on unmount
    return () => {
      pusherService.disconnect();
    };
  }, [formId]);

  const getProbabilityColor = (prob) => {
    if (prob >= 70) return 'text-green-600';
    if (prob >= 50) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getChangeColor = (change) => {
    if (change > 0) return 'text-green-600';
    if (change < 0) return 'text-red-600';
    return 'text-gray-600';
  };

  const getStatusBadge = (status) => {
    const statusMap = {
      'IN_PLAY': { color: 'bg-red-500', text: 'LIVE' },
      'PAUSED': { color: 'bg-orange-500', text: 'HT' },
      'FINISHED': { color: 'bg-gray-500', text: 'FT' },
      'SCHEDULED': { color: 'bg-blue-500', text: 'UPCOMING' }
    };

    const badge = statusMap[status] || { color: 'bg-gray-400', text: status };

    return (
      <span className={`${badge.color} text-white text-xs px-2 py-1 rounded font-bold`}>
        {badge.text}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="w-full max-w-6xl mx-auto p-6">
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading betting form...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-6xl mx-auto p-6">
      {/* Connection Status */}
      <div className="mb-6 flex items-center justify-between bg-white rounded-lg shadow p-4">
        <div>
          <h2 className="text-2xl font-bold">Live Match Updates</h2>
          <p className="text-sm text-gray-600">
            Updates happen automatically every 30 seconds during live matches
          </p>
        </div>
        <div className="flex items-center">
          <div
            className={`w-3 h-3 rounded-full mr-2 ${
              connected ? 'bg-green-500 animate-pulse' : 'bg-red-500'
            }`}
          />
          <span className="text-sm font-medium text-gray-700">
            {connected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </div>

      {/* Games Grid */}
      {games.length > 0 ? (
        <div className="grid gap-6 md:grid-cols-2">
          {games.map((game, index) => (
            <div
              key={game.game_id || index}
              className="bg-white rounded-lg shadow-lg p-6 border-2 border-gray-200 hover:border-blue-400 transition-all"
            >
              {/* Match Header */}
              <div className="mb-4">
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <h3 className="font-bold text-lg text-gray-900">{game.home_team}</h3>
                    <p className="text-gray-400 text-sm my-1">vs</p>
                    <h3 className="font-bold text-lg text-gray-900">{game.away_team}</h3>
                  </div>
                  
                  {/* Live Score */}
                  {game.current_score && (
                    <div className="text-center">
                      {getStatusBadge(game.status)}
                      <p className="text-3xl font-bold text-gray-900 mt-2">
                        {game.current_score}
                      </p>
                      {game.minute && (
                        <p className="text-sm text-gray-600 mt-1">{game.minute}'</p>
                      )}
                    </div>
                  )}
                  
                  {!game.current_score && game.kickoff_time && (
                    <div className="text-right">
                      {getStatusBadge('SCHEDULED')}
                      <p className="text-xs text-gray-600 mt-2">
                        {new Date(game.kickoff_time).toLocaleString()}
                      </p>
                    </div>
                  )}
                </div>
              </div>

              {/* Bet Information */}
              <div className="mb-4 p-3 bg-gray-50 rounded-lg">
                <div className="grid grid-cols-3 gap-2 text-sm">
                  <div>
                    <span className="text-gray-600 block">Bet Type</span>
                    <span className="font-medium">{game.bet_type}</span>
                  </div>
                  <div>
                    <span className="text-gray-600 block">Odds</span>
                    <span className="font-medium">{game.odds}</span>
                  </div>
                  <div>
                    <span className="text-gray-600 block">Stake</span>
                    <span className="font-medium">${game.stake}</span>
                  </div>
                </div>
              </div>

              {/* Prediction */}
              {(game.updated_prediction || game.initial_prediction) && (
                <div className="space-y-3">
                  <div className="flex justify-between items-center p-3 bg-blue-50 rounded-lg">
                    <span className="text-sm font-medium text-gray-700">
                      Win Probability:
                    </span>
                    <div className="flex items-center">
                      <span
                        className={`text-2xl font-bold ${getProbabilityColor(
                          (game.updated_prediction || game.initial_prediction).win_probability
                        )}`}
                      >
                        {((game.updated_prediction || game.initial_prediction).win_probability).toFixed(1)}%
                      </span>
                      {game.change !== undefined && game.change !== 0 && (
                        <span
                          className={`ml-2 text-sm font-medium ${getChangeColor(
                            game.change
                          )}`}
                        >
                          {game.change > 0 ? '↗' : '↘'} {Math.abs(game.change).toFixed(1)}%
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Confidence & EV */}
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div className="p-2 bg-gray-50 rounded">
                      <span className="text-gray-600 block">Confidence</span>
                      <span className="font-medium capitalize">
                        {(game.updated_prediction || game.initial_prediction).confidence}
                      </span>
                    </div>
                    {(game.updated_prediction?.expected_value !== undefined || 
                      game.initial_prediction?.expected_value !== undefined) && (
                      <div className="p-2 bg-gray-50 rounded">
                        <span className="text-gray-600 block">Expected Value</span>
                        <span
                          className={`font-medium ${
                            (game.updated_prediction?.expected_value || 
                             game.initial_prediction?.expected_value) > 0
                              ? 'text-green-600'
                              : 'text-red-600'
                          }`}
                        >
                          ${((game.updated_prediction?.expected_value || 
                              game.initial_prediction?.expected_value)).toFixed(2)}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Reasoning */}
                  {(game.updated_prediction?.reasoning || game.initial_prediction?.reasoning) && (
                    <div className="mt-3 pt-3 border-t">
                      <p className="text-xs font-medium text-gray-700 mb-2">
                        Analysis:
                      </p>
                      <ul className="text-xs text-gray-600 space-y-1">
                        {(game.updated_prediction?.reasoning || game.initial_prediction?.reasoning).map((reason, i) => (
                          <li key={i} className="flex items-start">
                            <span className="mr-2">•</span>
                            <span>{reason}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-12 bg-white rounded-lg shadow">
          <svg
            className="w-16 h-16 mx-auto mb-4 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
          <p className="text-lg text-gray-600">No games in this betting form</p>
        </div>
      )}

      {/* Recent Updates Log */}
      {updates.length > 0 && (
        <div className="mt-8 bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-bold mb-4">Recent Updates</h3>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {updates.map((update, index) => (
              <div
                key={index}
                className="text-sm p-3 bg-gray-50 rounded flex justify-between items-center"
              >
                <span className="text-gray-700">
                  {update.updates?.length || 0} game(s) updated
                </span>
                <span className="text-xs text-gray-500">
                  {new Date(update.timestamp).toLocaleTimeString()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}