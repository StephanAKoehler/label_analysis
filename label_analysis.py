#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep  1 20:42:45 2021

class labels
and
class strings_compare

@author: stephankoehler
"""

import pandas as pd
import numpy as np
import re
from rapidfuzz import fuzz, process, utils

    
def fuzzy_extractBests(  query, choices, scorer=fuzz.WRatio, processor = utils.default_process, limit=5, score_cutoff=85, allow = None, allow_len = 2 ):
    '''
    extension of process.extractBests, which allows for single typo ("typo") or single missing character ("missing") or either ("either")
    Parameters
    ----------
    query : TYPE
        DESCRIPTION.
    choices : TYPE
        DESCRIPTION.
    scorer : TYPE, optional
        DESCRIPTION. The default is fuzz.WRatio.
    processor : TYPE, optional
        DESCRIPTION. The default is utils.default_process.
    limit : TYPE, optional
        DESCRIPTION. The default is 5.
    score_cutoff : TYPE, optional
        DESCRIPTION. The default is 0.
    allow : allows single  mistake
        The default is None
        'missing': 1 missing character
        'typo': 1 typo
        'either': typo or missing

    allow_len : cutoff query length to enable allow
        DESCRIPTION. The default is 2.

    Returns
    -------
    choice_score : list of tuples similar to process.extractBests, except that there are allowances for typos or missing chars
        DESCRIPTION.

    '''
    choice_score_ = process.extractBests(query, choices, processor = processor, limit = limit, score_cutoff = 0 )    
    choice_score = [c_s for c_s in choice_score_ if c_s[1] > score_cutoff ]
    if choice_score:
        return choice_score
    if allow in ['typo', 'missing', 'either'] and len( query ) >= allow_len:
        alt_score = [ np.round( (len( query ) + len( c_s[0] ))*(1 - c_s[1]/100) ) for c_s in choice_score_] #type = 2, missing = 1
        if allow == 'typo':
            choice_score = [ c_s for i, c_s in enumerate( choice_score_ )  if alt_score[i] == 2 ]
        elif allow == 'either':
            choice_score = [ c_s for i, c_s in enumerate( choice_score_ )  if alt_score[i] in [1, 2] ]
        else: #missing
            choice_score = [ c_s for i, c_s in enumerate( choice_score_ )  if alt_score[i] == 1 ]
        return choice_score
    else:
        return []
             
print( fuzzy_extractBests( 'wor', ['word', 'wxr'], score_cutoff = 95, allow = 'typo') )
    
#%%
def fuzzy_dict( key = 'wor', dict_ = dict( zip( ['word', 'thing', 'stuff'], [0, 1,2])), score_cutoff = 90, pass_through = True, allow = 'either' ):    
    '''
    dict that uses fuzzy to match key, or passes the key
    Parameters
    ----------
    key : key for dict_
    dict_ : TYPE, optional
        DESCRIPTION. The default is dict( zip( ['word', 'thing', 'stuff'], [0, 1,2])).
    score_cutoff : TYPE, optional
        DESCRIPTION. The default is 90.
    pass_through : bool
        if True and no key match, then returns key (the input)
    allow : None, 'missing', 'typo' or 'either' ( see 'fuzzy_extractBests' )'
    
    Returns
    -------
        dict_[key_], where key_ is fuzzy match to key
        or key if no match, and pass_through = True

    '''
    if score_cutoff == 100 or key in dict_:
        return dict_[key], 100
    choice_score = fuzzy_extractBests(  key, dict_.keys(), score_cutoff=score_cutoff, allow = allow )
    if choice_score:
        key = choice_score[0][0]
        return dict_[key], choice_score[0][1]
    assert pass_through
    return key, np.NaN

# print( fuzzy_dict( ))
#%%
def trunc_list( list_, list_for_truncating, include_intersect = True, count = -1 ):
    last_i = None
    if count < 0:
        for i in reversed( range( len( list_ ) ) ):
            if list_[i] in list_for_truncating:
                count += 1
                last_i = i
                if count == 0:
                    break
        if last_i != None:
            if include_intersect:
                return list_[:last_i+1]
            else:
                return list_[:last_i]
        return list_
    elif count > 0:
        for i in range( len( list_ ) ):
            if list_[i] in list_for_truncating:
                count -= 1
                last_i = i
                if count == 0:
                    break
        if last_i != None:
            if include_intersect:
                return list_[:last_i+1]
            else:
                return list_[:last_i]
        return list_
    else:
        return list_

# print( trunc_list( [0,1,2,3], [0,2, 3, 4], True, 1 ) ) 

def DataFrame2int( df ):
    '''
    converts columns to integers where possible

    Parameters
    ----------
    df : pandas DataFrame


    Returns
    -------
    df : converted DataFrame

    '''
    for i in range( df.shape[1] ):
        try:
            tmp = df.iloc[:,i].astype( int )
            if ( tmp == df.iloc[:,i] ).all():
                df.iloc[:,i] = tmp
        except:
            pass
    return df
#%%

class labelings():
    '''
    class for dealing with all sorts of labels: address, company, name
    '''
    
    def __init__(self, file = 'common_abbreviations.xlsx', fuzzy_threshold = 90, fuzzy_numeric_threshold = 100, fuzzy_dict_score_cut_off = 90, fuzzy_numeric_score_cut_off = 100 ):
        self.fuzzy_threshold  = fuzzy_threshold 
        self.fuzzy_numeric_threshold = fuzzy_numeric_threshold
        self.fuzzy_numeric_score_cut_off = fuzzy_numeric_score_cut_off
        common_abbreviations = pd.read_excel( file, sheet_name = None, header = None, )
        self.file = file        
        self.fuzzy_dict_score_cut_off = fuzzy_dict_score_cut_off
        self.listing = {}
        self.dictionary = {}
        for k in common_abbreviations:#['cardinals']:#common_abbreviations:
        # for k in ['cardinals']:
            starting = int( common_abbreviations[k].iloc[:, :1].where(common_abbreviations[k].iloc[:, :1]=='*****').dropna().index.values )+1
            common_abbreviations[k] = DataFrame2int( common_abbreviations[k].copy().iloc[starting:, :] ).applymap( lambda x: str(x).lower() )
            self.listing[k] = [v.lower() for v in common_abbreviations[k].values.ravel() if isinstance( v, str )]
            self.dictionary[k] = dict( zip(common_abbreviations[k].iloc[:,0], common_abbreviations[k].iloc[:,1] ) )
            
    def standardize_street_address( self, string = '1024 E 50th stree', fuzzy_threshold = None, return_list = True, return_suffix = False ):
        string_split = self.standardize_address( string, fuzzy_threshold, return_list = True )
        suffix = None
        for i in range( len( string_split )-1, -1, -1 ):
            flag = string_split[i].lower() in self.dictionary['postal suffix'].values()
            if flag:  
                suffix = string_split[i]
                break       
        if flag:
            string_split = string_split[:i]
        if return_list:
            thing = string_split
        else:
            thing = ' '.join( string_split )
        if return_suffix:
            return thing, suffix
        else:
            return thing
    
    def remove_cardinals( self, string, fuzzy_threshold = None ):
        if fuzzy_threshold == None:
            fuzzy_threshold = self.fuzzy_threshold       
        flag = isinstance( string, list )
        if flag:
            string_split = string
        else:
            string_split = string.split()
        for i, w in enumerate( string_split ):
            w_split = re.sub( r'(\D+)(\d+)', r'\1 \2', re.sub( r'(\d+)(\D+)', r'\1 \2', w) ).split()
            for j in range( len( w_split ) ):
                w_split[j] =  fuzzy_dict(  w_split[j], self.dictionary['cardinals'], fuzzy_threshold )
            string_split[i] = ''.join( w_split )
        if flag:
            return string_split
        return ' '.join( string_split )
    
    def remove_ordinals( self, string, fuzzy_threshold = None ):
        if fuzzy_threshold == None:
            fuzzy_threshold = self.fuzzy_threshold        
        flag = isinstance( string, list )
        if flag:
            string_split = string
        else:
            string_split = string.split()
        for i, w in enumerate( string_split ):
            w_split = re.sub( r'(\D+)(\d+)', r'\1 \2', re.sub( r'(\d+)(\D+)', r'\1 \2', w) ).split()
            for j in range( len( w_split ) ):
                w_split[j] =  fuzzy_dict(  w_split[j], self.dictionary['ordinals'], fuzzy_threshold )
            string_split[i] = ''.join( w_split )
        if flag:
            return string_split
        return ' '.join( string_split )
                                
    def standardize_states(string, require_caps4abbrev = True):
        '''                
        Parameters
        ----------
        string : TYPE
            DESCRIPTION.

        Returns
        -------
        None.

        '''
        
    def standardize_person(full_name):
        '''
        input is full_name with prefix (i.e. Mr.) and suffix (i.e. PhD)

        Returns
        -------
        name, prefix, suffix

        '''
        pass
    
    def compare_person( person1, person2 ):
        pass    
        
    def standardize_building_name(self, string = '13thirteen Randolph Street Lofts', fuzzy_threshold = None ):
        if fuzzy_threshold == None:
            fuzzy_threshold = self.fuzzy_threshold
            
        string_split = self.standardize_address( string, fuzzy_threshold )
        return string_split
        
    def city():
        pass
            
    def compare_street_address( self, string1_split, string2_split, fuzzy_threshold = None, fuzzy_numeric_threshold = None, compare_suffix = None ):
        '''
        compares street address of string1_split, string2_split
        note: will split() string1_split or string2_split if necessary

        Parameters
        ----------
        string1_split : TYPE
            DESCRIPTION.
        string2_split : TYPE
            DESCRIPTION.
        fuzzy_threshold : TYPE, optional
            DESCRIPTION. The default is None.
        fuzzy_numeric_threshold : TYPE, optional
            DESCRIPTION. The default is None.
        compare_suffix : TYPE, optional
            True: suffixes must equal (or both missing )
            False: ignores suffix
            None: fogives missing suffix, but if both are present must equal
        Returns
        -------
        TYPE
            DESCRIPTION.

        '''
        if fuzzy_threshold == None:
            fuzzy_threshold = self.fuzzy_threshold   
        suffix1 = None
        suffix2 = None
        if compare_suffix:
            string1_split, suffix1 = self.standardize_street_address(  string1_split, fuzzy_threshold = fuzzy_threshold, return_suffix = compare_suffix )
            string2_split, suffix1 = self.standardize_street_address(  string2_split, fuzzy_threshold = fuzzy_threshold, return_suffix = compare_suffix )
            return self.compare( string1_split, string2_split, 
                            fuzzy_threshold = fuzzy_threshold, fuzzy_numeric_threshold = fuzzy_numeric_threshold, return_pair_score = False ) & \
                    self.compare( suffix1, suffix2, 
                            fuzzy_threshold = fuzzy_threshold, fuzzy_numeric_threshold = fuzzy_numeric_threshold, return_pair_score = False )
        elif compare_suffix == False:
            string1_split = self.standardize_street_address(  string1_split, fuzzy_threshold = fuzzy_threshold, return_suffix = compare_suffix )
            string2_split = self.standardize_street_address(  string2_split, fuzzy_threshold = fuzzy_threshold, return_suffix = compare_suffix )
            return self.compare( string1_split, string2_split, 
                            fuzzy_threshold = fuzzy_threshold, fuzzy_numeric_threshold = fuzzy_numeric_threshold, return_pair_score = False )
        else:
            string1_split, suffix1 = self.standardize_street_address(  string1_split, fuzzy_threshold = fuzzy_threshold, return_suffix = True )
            string2_split, suffix2 = self.standardize_street_address(  string2_split, fuzzy_threshold = fuzzy_threshold, return_suffix = True )
            if suffix1 == None or suffix2 == None:
                return self.compare( string1_split, string2_split, 
                            fuzzy_threshold = fuzzy_threshold, fuzzy_numeric_threshold = fuzzy_numeric_threshold, return_pair_score = False )

            return self.compare( string1_split, string2_split, 
                            fuzzy_threshold = fuzzy_threshold, fuzzy_numeric_threshold = fuzzy_numeric_threshold, return_pair_score = False ) & \
                    self.compare( suffix1, suffix2, 
                            fuzzy_threshold = fuzzy_threshold, fuzzy_numeric_threshold = fuzzy_numeric_threshold, return_pair_score = False )
        
            
    
    def compare( self, string1_split, string2_split, fuzzy_threshold = None, fuzzy_numeric_threshold = None, return_pair_score = False ):
        '''
        compare string1_split with string2_split using clearing-the-fuzzy_threshold-bar (greedy?) 
        with the assumption that the terser string_split contains critical sub-strings that MUST be matched to the longer string_split using fuzzy_threshold
        we swap string1_split with string2_split such that string1_split is shorter (terse form of information)

        Parameters
        ----------
        string1_split : list of str (or str which gets .split() )
        string2_split : list of str (or str which gets .split() )
        fuzzy_threshold : numeric (0-100), optional
            DESCRIPTION. The default is self.fuzzy_threshold.
        fuzzy_numeric_threshold : numeric (0-100), optional
            DESCRIPTION. The default is self.fuzzy_numeric_threshold.
        return_pair_score : TYPE, optional
            DESCRIPTION. The default is False.
            if False then only returns if match was successful
            if True, then returns 
                match successful,
                tuple of (str1, str2, index2, score_match)
                list of missing str2 from string2_split

        Returns
        -------
        TYPE
            DESCRIPTION.

        '''
        if string1_split == string2_split:
            return True
        elif string1_split == None or string2_split == None:
            return False
        suffix1 = None
        suffix2 = None
        if isinstance( string1_split, tuple ):
            suffix1 = string1_split[1]
            string1_split = string1_split[0]
        if isinstance( string2_split, tuple ):
            suffix2 = string2_split[1]
            string2_split = string2_split[0]
        if not isinstance( string1_split, list ):
            string1_split = string1_split.split()
        if not isinstance( string2_split, list ):
            string2_split = string2_split.split()
        if fuzzy_threshold == None:
            fuzzy_threshold = self.fuzzy_threshold
        if fuzzy_numeric_threshold == None:
            fuzzy_numeric_threshold = self.fuzzy_numeric_threshold
            
        if len( string1_split ) > len( string2_split ):
            string1_split, string2_split = string2_split, string1_split
        
        flag_compare = True
        pair_score = []    
        first_index = -1   
        indices2 = []
        for i, s in enumerate( string1_split ):
            if s.isnumeric():
                indices_score = process.extractIndices( s, string2_split[first_index+1:], scorer= fuzz.ratio, score_cutoff = fuzzy_numeric_threshold )
            else:
                indices_score = process.extractIndices( s, string2_split[first_index+1:], scorer= fuzz.ratio, score_cutoff = fuzzy_threshold )
            if indices_score:
                first_index_score = indices_score[np.argmin( [i_s[0] for i_s in indices_score] ) ]
                first_index += 1+first_index_score[0]
                if return_pair_score:
                    pair_score.append( (s, string2_split[first_index], first_index, first_index_score[1] ) )
                    indices2.append( first_index )
            else:
                flag_compare = False
                pair_score.append( (s, None, -1) )
            if not return_pair_score and not flag_compare:
               break
        if suffix1 == None:
            pass
        if suffix2 == None:
            pass
        else:
            flag_compare &= suffix1 == suffix2 
        if return_pair_score:
            return flag_compare, pair_score, [s for i, s in enumerate( string2_split ) if not i in indices2]
        else:
            return flag_compare
        
    def standardize(self, string = 'Exxonmobil corporation', dictionaries = None, fuzzy_threshold = None, return_list = True ):
        if fuzzy_threshold == None:
            fuzzy_threshold = self.fuzzy_threshold
            
        if isinstance( string, list ):
            string = ' '.join( string )
        string = re.sub( '\W', ' ', re.sub( ' & ', ' and ', string.lower() ) )
        string_split = string.split()
        for i, s in enumerate( string_split ):
            best_score = fuzzy_threshold
            best_val = None
            for d in dictionaries:
                # print(i, d, string_split[i] )
                value_score = fuzzy_dict( s, self.dictionary[d], score_cutoff = fuzzy_threshold, pass_through=True, allow = 'either')
                if value_score[1] > best_score:
                    best_val = value_score[0]
                    best_score = value_score[1]
                    if d == 'oridnals':
                        best_val = value_score[0][:-2]
                elif s in self.dictionary[d].values():
                    best_val = s
                    best_score = 100                    
            if best_val:
                string_split[i] = best_val.upper()
        if return_list:
            return string_split
        else:
            return ' '.join( string_split )        
    
    def standardize_company(self, string = 'Exxonmobil corporation', fuzzy_threshold = None, return_list = True ):
        return self.standardize( string, dictionaries = ['compass directions', 'cardinals', 'ordinals', 'business suffix', 'states'], 
            fuzzy_threshold = fuzzy_threshold, return_list = return_list )

    def standardize_address(self, string = 'Exxonmobil corporation', fuzzy_threshold = None, return_list = True ):
        return self.standardize( string, dictionaries = ['compass directions', 'cardinals', 'ordinals', 'postal suffix', 'states'], 
            fuzzy_threshold = fuzzy_threshold, return_list = return_list )    
        
if __name__ == "__main__":
    self = labelings()
    print( self.standardize_street_address('904 Montana', fuzzy_threshold = 90, return_suffix = True ) )
    print( self.compare( ('5710 duck creek', 'DR'), ('5710 duck creek', 'DR')))
    # print( self.compare( self.standardize_street_address('4030 N Central Expy, Dallas', fuzzy_threshold = 90, return_suffix = True ), 
    #                     self.standardize_street_address('4030 N Central expressway', fuzzy_threshold = 90, return_suffix = True ) ) )
    
    print( self.standardize_company() )
    
    
    # self.compare( None, 'adf')
    # print( self.compare( '1024 E 50', 'the 1024 E s 50', return_pair_score = True ) )
    # print( self.compare_street_address( '1024 E 50', 'the 1024 east s 50 street' ) )
    # print( self.compare_street_address( '1024 E 50', 'the 1024 east s 50 street', compare_suffix = None ) )
    # print( self.compare_street_address( '1024 E 50', 'the 1024 east s 50 street Chicago', compare_suffix = None ) )
    # print( self.compare_street_address( '1024 E 50', 'the 104 east s 50 street Chicago', fuzzy_numeric_threshold = 80, compare_suffix = None ) )

