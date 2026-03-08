import React, { useState, useCallback, useRef } from 'react';
import {
  View,
  Text,
  TextInput,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Colors } from '../constants';
import { schoolsApi } from '../services/api';
import type { School } from '../types';

interface Props {
  currentLat?: number;
  currentLng?: number;
  onSelect: (school: School) => void;
  nearbySchools?: School[];
}

export default function SchoolSearchInput({
  currentLat,
  currentLng,
  onSelect,
  nearbySchools = [],
}: Props) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<School[]>(nearbySchools);
  const [isSearching, setIsSearching] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const searchTimer = useRef<ReturnType<typeof setTimeout>>(undefined);

  const search = useCallback(
    async (text: string) => {
      if (text.length === 0) {
        setResults(nearbySchools);
        return;
      }
      try {
        setIsSearching(true);
        const data = await schoolsApi.search(text, currentLat, currentLng);
        setResults(data);
      } catch {
        // Keep existing results on error
      } finally {
        setIsSearching(false);
      }
    },
    [currentLat, currentLng, nearbySchools]
  );

  const handleTextChange = useCallback(
    (text: string) => {
      setQuery(text);
      if (searchTimer.current) clearTimeout(searchTimer.current);
      searchTimer.current = setTimeout(() => search(text), 300);
    },
    [search]
  );

  const handleSelect = useCallback(
    (school: School) => {
      setSelectedId(school.id);
      setQuery(school.name);
      onSelect(school);
    },
    [onSelect]
  );

  const formatDistance = (meters?: number) => {
    if (!meters) return '';
    if (meters < 1000) return `${Math.round(meters)}m`;
    return `${(meters / 1000).toFixed(1)}km`;
  };

  return (
    <View style={styles.container}>
      <View style={styles.inputContainer}>
        <Ionicons name="search" size={20} color={Colors.gray} />
        <TextInput
          style={styles.input}
          placeholder="学校名を入力"
          placeholderTextColor={Colors.textTertiary}
          value={query}
          onChangeText={handleTextChange}
          autoCorrect={false}
          clearButtonMode="while-editing"
        />
        {isSearching && <ActivityIndicator size="small" color={Colors.primary} />}
      </View>

      {query.length === 0 && results.length > 0 && (
        <Text style={styles.sectionLabel}>近くの学校</Text>
      )}

      <FlatList
        data={results}
        keyExtractor={(item) => item.id}
        keyboardShouldPersistTaps="handled"
        renderItem={({ item }) => (
          <TouchableOpacity
            style={[styles.resultItem, selectedId === item.id && styles.resultItemSelected]}
            onPress={() => handleSelect(item)}
            activeOpacity={0.6}
          >
            <View style={styles.resultIcon}>
              <Ionicons
                name={selectedId === item.id ? 'checkmark-circle' : 'school-outline'}
                size={22}
                color={selectedId === item.id ? Colors.primary : Colors.textSecondary}
              />
            </View>
            <View style={styles.resultContent}>
              <Text
                style={[
                  styles.schoolName,
                  selectedId === item.id && styles.schoolNameSelected,
                ]}
              >
                {item.name}
              </Text>
              <Text style={styles.schoolAddress} numberOfLines={1}>
                {item.address}
              </Text>
            </View>
            {item.distanceFromHome != null && (
              <Text style={styles.distance}>
                {formatDistance(item.distanceFromHome)}
              </Text>
            )}
          </TouchableOpacity>
        )}
        ListEmptyComponent={
          query.length > 0 && !isSearching ? (
            <Text style={styles.emptyText}>学校が見つかりませんでした</Text>
          ) : null
        }
        style={styles.list}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.white,
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 12,
    marginHorizontal: 16,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: Colors.border,
    gap: 10,
  },
  input: {
    flex: 1,
    fontSize: 16,
    color: Colors.text,
  },
  sectionLabel: {
    fontSize: 13,
    fontWeight: '600',
    color: Colors.textSecondary,
    marginHorizontal: 20,
    marginTop: 8,
    marginBottom: 6,
  },
  list: {
    flex: 1,
  },
  resultItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 14,
    paddingHorizontal: 16,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: Colors.border,
  },
  resultItemSelected: {
    backgroundColor: Colors.primaryLight,
  },
  resultIcon: {
    marginRight: 12,
  },
  resultContent: {
    flex: 1,
  },
  schoolName: {
    fontSize: 15,
    fontWeight: '500',
    color: Colors.text,
    marginBottom: 2,
  },
  schoolNameSelected: {
    color: Colors.primary,
    fontWeight: '700',
  },
  schoolAddress: {
    fontSize: 12,
    color: Colors.textSecondary,
  },
  distance: {
    fontSize: 13,
    color: Colors.textTertiary,
    fontWeight: '500',
    marginLeft: 8,
  },
  emptyText: {
    textAlign: 'center',
    color: Colors.textSecondary,
    paddingVertical: 30,
    fontSize: 14,
  },
});
