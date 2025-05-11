import time
import logging
from typing import Tuple, Optional
import redis.asyncio as redis

logger = logging.getLogger("api_gateway.rate_limiting")

class RateLimiter:
    """
    Limiteur de taux basé sur Redis pour limiter le nombre de requêtes par client
    """
    def __init__(
        self,
        redis_url: Optional[str],
        default_limit: int = 100,
        default_period: int = 60
    ):
        self.redis_url = redis_url
        self.default_limit = default_limit
        self.default_period = default_period
        self.redis_client = None
        
        # Initialiser le client Redis si l'URL est fournie
        if self.redis_url:
            try:
                self.redis_client = redis.from_url(self.redis_url)
                logger.info("Rate limiter initialized with Redis")
            except Exception as e:
                logger.error(f"Failed to initialize Redis client: {str(e)}")
                logger.warning("Using in-memory rate limiting (not suitable for production)")
                
        else:
            logger.warning("No Redis URL provided. Using in-memory rate limiting (not suitable for production)")
            
        # Dictionnaire pour le limiteur en mémoire (si Redis n'est pas disponible)
        self.memory_store = {}
    
    async def check(
        self, 
        client_id: str,
        limit: int = None,
        period: int = None
    ) -> Tuple[bool, int, int]:
        """
        Vérifier si un client a dépassé sa limite de taux
        
        Args:
            client_id: Identifiant unique du client
            limit: Limite de requêtes (utilise la valeur par défaut si non spécifié)
            period: Période en secondes (utilise la valeur par défaut si non spécifié)
            
        Returns:
            Tuple[bool, int, int]: (autorisé, restant, temps_réinitialisation)
        """
        # Utiliser les valeurs par défaut si non spécifiées
        limit = limit or self.default_limit
        period = period or self.default_period
        
        # Utiliser Redis si disponible, sinon utiliser le stockage en mémoire
        if self.redis_client:
            return await self._check_redis(client_id, limit, period)
        else:
            return self._check_memory(client_id, limit, period)
    
    async def _check_redis(
        self,
        client_id: str,
        limit: int,
        period: int
    ) -> Tuple[bool, int, int]:
        """
        Implémenter la limite de taux avec Redis en utilisant un algorithme de fenêtre glissante
        """
        try:
            # Clé unique pour ce client et cette période
            key = f"rate_limit:{client_id}:{period}"
            now = time.time()
            pipe = self.redis_client.pipeline()
            
            # Supprimer les timestamps plus anciens que la période
            cutoff = now - period
            await pipe.zremrangebyscore(key, 0, cutoff)
            
            # Ajouter le timestamp actuel
            await pipe.zadd(key, {str(now): now})
            
            # Compter le nombre de requêtes dans la période
            await pipe.zcard(key)
            
            # Définir une expiration sur la clé
            await pipe.expire(key, period)
            
            # Exécuter la pipeline
            results = await pipe.execute()
            request_count = results[2]
            
            # Vérifier si la limite est dépassée
            allowed = request_count <= limit
            remaining = max(0, limit - request_count)
            
            # Calculer le temps de réinitialisation
            if remaining > 0:
                reset_time = int(now) + period
            else:
                # Obtenir le timestamp de la requête la plus ancienne
                oldest = await self.redis_client.zrange(key, 0, 0, withscores=True)
                if oldest:
                    reset_time = int(oldest[0][1]) + period
                else:
                    reset_time = int(now) + period
            
            return allowed, remaining, reset_time
            
        except Exception as e:
            logger.error(f"Redis rate limiting error: {str(e)}")
            # En cas d'erreur, autoriser la requête
            return True, limit, int(time.time()) + period
    
    def _check_memory(
        self,
        client_id: str,
        limit: int,
        period: int
    ) -> Tuple[bool, int, int]:
        """
        Implémenter la limite de taux en mémoire
        """
        now = time.time()
        
        # Clé unique pour ce client et cette période
        key = f"{client_id}:{period}"
        
        # Initialiser l'entrée si elle n'existe pas
        if key not in self.memory_store:
            self.memory_store[key] = []
        
        # Supprimer les timestamps plus anciens que la période
        cutoff = now - period
        self.memory_store[key] = [ts for ts in self.memory_store[key] if ts > cutoff]
        
        # Vérifier si la limite est dépassée
        request_count = len(self.memory_store[key])
        allowed = request_count < limit
        
        # Ajouter le timestamp actuel si autorisé
        if allowed:
            self.memory_store[key].append(now)
        
        # Calculer le nombre restant
        remaining = max(0, limit - len(self.memory_store[key]))
        
        # Calculer le temps de réinitialisation
        if remaining > 0:
            reset_time = int(now) + period
        else:
            # Obtenir le timestamp de la requête la plus ancienne
            oldest = min(self.memory_store[key]) if self.memory_store[key] else now
            reset_time = int(oldest + period)
        
        # Nettoyer périodiquement le stockage en mémoire pour éviter les fuites de mémoire
        if now % 60 < 1:  # Nettoyer toutes les minutes environ
            self._clean_memory_store()
        
        return allowed, remaining, reset_time
    
    def _clean_memory_store(self):
        """
        Nettoyer les entrées périmées du stockage en mémoire
        """
        now = time.time()
        keys_to_delete = []
        
        for key, timestamps in self.memory_store.items():
            _, period = key.split(":")
            period = int(period)
            cutoff = now - period
            
            # Supprimer les timestamps plus anciens que la période
            self.memory_store[key] = [ts for ts in timestamps if ts > cutoff]
            
            # Si la liste est vide, marquer la clé pour suppression
            if not self.memory_store[key]:
                keys_to_delete.append(key)
        
        # Supprimer les clés vides
        for key in keys_to_delete:
            del self.memory_store[key]