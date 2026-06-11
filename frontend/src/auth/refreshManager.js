export const createRefreshManager = ({
  refreshRequest,
  getRefreshToken,
  setAccessToken,
  setRefreshToken,
  clearAuthTokens,
}) => {
  let refreshPromise = null;

  const refreshAccessToken = async () => {
    if (refreshPromise) {
      return refreshPromise;
    }

    const refreshToken = getRefreshToken();
    if (!refreshToken) {
      throw new Error('Refresh token ausente');
    }

    refreshPromise = refreshRequest(refreshToken)
      .then((response) => {
        const accessToken = response?.data?.access_token;
        const nextRefreshToken = response?.data?.refresh_token;

        if (!accessToken) {
          throw new Error('Access token ausente na renovacao');
        }

        setAccessToken(accessToken);
        if (nextRefreshToken) {
          setRefreshToken(nextRefreshToken);
        }
        return accessToken;
      })
      .catch((error) => {
        clearAuthTokens();
        throw error;
      })
      .finally(() => {
        refreshPromise = null;
      });

    return refreshPromise;
  };

  return { refreshAccessToken };
};
